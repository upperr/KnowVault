"""
RAG 系统测试脚本 - 评估问答准确率
使用方法：python scripts/test_accuracy.py
"""
import json
import httpx
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any
import re

# API 配置
API_BASE_URL = "http://localhost:8000"
ASK_ENDPOINT = f"{API_BASE_URL}/api/ask"

# 测试数据路径
TEST_DATA_PATH = Path(__file__).parent.parent / "tests" / "test_data1.json"


def load_test_data(path: Path) -> List[Dict[str, Any]]:
    """加载测试数据"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_model_answer(question: str, question_type: str, timeout: int = 30) -> str:
    """调用 API 获取模型答案"""
    # 根据题型添加提示，让模型直接输出答案
    type_prompts = {
        "单选": "单选题（仅输出正确选项，如：A）：",
        "多选": "多选题（仅输出正确选项，如：ABD）：",
        "判断": "判断题（仅输出正确或错误）：",
        "简答": "简答题（简洁回答）："
    }
    prompt = type_prompts.get(question_type, "题目：")
    full_question = f"{prompt}{question}"
    
    try:
        response = httpx.post(
            ASK_ENDPOINT,
            json={"question": full_question, "use_history": False},
            timeout=timeout
        )
        response.raise_for_status()
        result = response.json()
        return result.get("answer", "")
    except Exception as e:
        print(f"  ⚠️ API 调用失败：{e}")
        return ""


def normalize_answer(answer: str) -> str:
    """标准化答案：去除空格、标点，转大写"""
    answer = answer.upper()
    answer = re.sub(r'[^A-Z]', '', answer)
    return answer


def extract_answer_from_model_response(model_response: str, question_type: str) -> str:
    """从模型回答中提取答案字母"""
    model_response = model_response.strip()
    
    patterns = [
        r'答案 [：:\s]*([A-D]+)',
        r'【答案】[：:\s]*([A-D]+)',
        r'^([A-D]+)[\s:.]',
        r'^([A-D]+)$',
        r'选择 ([A-D]+)',
        r'正确 (?:选项)?[是：:]*([A-D]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, model_response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    
    first_line = model_response.split('\n')[0].strip()
    match = re.search(r'([A-D]+)', first_line, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    return ""


def compare_answers(model_answer: str, standard_answer: str, question_type: str) -> bool:
    """比对答案"""
    if not model_answer.strip():
        return False
    
    standard_normalized = normalize_answer(standard_answer)
    
    if question_type in ["单选", "判断"]:
        model_extracted = extract_answer_from_model_response(model_answer, question_type)
        return model_extracted == standard_normalized
    
    elif question_type == "多选":
        model_extracted = extract_answer_from_model_response(model_answer, question_type)
        model_set = set(model_extracted)
        standard_set = set(standard_normalized)
        return model_set == standard_set
    
    elif question_type == "简答":
        standard_answer = standard_answer.strip()
        keywords = re.findall(r'[\u4e00-\u9fa5A-Za-z0-9]+', standard_answer)
        if not keywords:
            return False
        matched = sum(1 for kw in keywords if kw in model_answer)
        return matched >= len(keywords) * 0.5
    
    return False


def run_test(test_data: List[Dict[str, Any]], verbose: bool = True) -> Dict[str, Any]:
    """运行测试"""
    results = defaultdict(lambda: {"correct": 0, "total": 0, "details": []})
    
    total = len(test_data)
    print(f"\n{'='*60}")
    print(f"开始测试 - 共 {total} 道题")
    print(f"{'='*60}\n")
    
    for i, item in enumerate(test_data, 1):
        question_type = item.get("题型", "未知")
        question = item.get("题目", "")
        standard_answer = item.get("标准答案", "")
        
        print(f"[{i}/{total}] {question_type}: {question[:50]}...")
        model_answer = get_model_answer(question, question_type)
        
        is_correct = compare_answers(model_answer, standard_answer, question_type)
        
        results[question_type]["total"] += 1
        if is_correct:
            results[question_type]["correct"] += 1
        
        results[question_type]["details"].append({
            "question": question,
            "standard_answer": standard_answer,
            "model_answer": model_answer[:200] if model_answer else "",
            "correct": is_correct
        })
        
        status = "✅" if is_correct else "❌"
        if verbose:
            model_extracted = extract_answer_from_model_response(model_answer, question_type)
            print(f"  {status} 标准答案：{standard_answer} | 模型答案：{model_extracted or '未提取'}")
            if not is_correct and verbose:
                print(f"     完整回答：{model_answer[:100]}...")
        print()
    
    return dict(results)


def print_statistics(results: Dict[str, Any]):
    """打印统计结果"""
    print(f"\n{'='*60}")
    print("测试结果统计")
    print(f"{'='*60}\n")
    
    total_correct = 0
    total_all = 0
    
    print("【按题型统计】")
    print(f"{'题型':<10} {'正确':<8} {'总数':<8} {'准确率':<10}")
    print("-" * 40)
    
    for qtype in sorted(results.keys()):
        data = results[qtype]
        correct = data["correct"]
        total = data["total"]
        accuracy = correct / total * 100 if total > 0 else 0
        
        total_correct += correct
        total_all += total
        
        print(f"{qtype:<10} {correct:<8} {total:<8} {accuracy:>6.1f}%")
    
    print("-" * 40)
    
    overall_accuracy = total_correct / total_all * 100 if total_all > 0 else 0
    print(f"\n【总体统计】")
    print(f"总题数：{total_all}")
    print(f"正确数：{total_correct}")
    print(f"总体准确率：{overall_accuracy:.1f}%")
    
    output_path = Path(__file__).parent.parent / "tests" / "test_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n详细结果已保存至：{output_path}")
    
    return {
        "total": total_all,
        "correct": total_correct,
        "accuracy": overall_accuracy,
        "by_type": {
            qtype: {
                "correct": data["correct"],
                "total": data["total"],
                "accuracy": data["correct"] / data["total"] * 100 if data["total"] > 0 else 0
            }
            for qtype, data in results.items()
        }
    }


def main():
    """主函数"""
    print("="*60)
    print("RAG 系统问答准确率测试")
    print("="*60)
    
    if not TEST_DATA_PATH.exists():
        print(f"❌ 测试数据文件不存在：{TEST_DATA_PATH}")
        return
    
    test_data = load_test_data(TEST_DATA_PATH)
    print(f"已加载 {len(test_data)} 道测试题目")
    
    try:
        response = httpx.get(f"{API_BASE_URL}/api/status", timeout=5)
        if response.status_code == 200:
            print(f"✅ API 服务正常：{API_BASE_URL}")
        else:
            print(f"⚠️ API 返回异常状态：{response.status_code}")
    except Exception as e:
        print(f"❌ 无法连接 API 服务：{e}")
        print(f"请确保服务正在运行：http://localhost:8000")
        return
    
    results = run_test(test_data, verbose=True)
    stats = print_statistics(results)
    
    print(f"\n{'='*60}")
    print("测试完成！")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
