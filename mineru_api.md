
## url 批量上传解析
### 接口说明

适用于本地文件上传解析的场景，可通过此接口批量申请文件上传链接，上传文件后，系统会自动提交解析任务 注意：

申请的文件上传链接有效期为 24 小时，请在有效期内完成文件上传
上传文件时，无须设置 Content-Type 请求头
文件上传完成后，无须调用提交解析任务接口。系统会自动扫描已上传完成文件自动提交解析任务
单次申请链接不能超过 50 个
header头中需要包含 Authorization 字段，格式为 Bearer + 空格 + Token

### Python 请求示例（适用于pdf、word、ppt、excel、图片文件）：

```python
import requests

token = "API管理页面自定创建的token"
url = "https://mineru.net/api/v4/file-urls/batch"
header = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}
data = {
    "files": [
        {"name":"demo.pdf", "data_id": "abcd"}
    ],
    "model_version":"vlm"
}
file_path = ["demo.pdf"]
try:
    response = requests.post(url,headers=header,json=data)
    if response.status_code == 200:
        result = response.json()
        print('response success. result:{}'.format(result))
        if result["code"] == 0:
            batch_id = result["data"]["batch_id"]
            urls = result["data"]["file_urls"]
            print('batch_id:{},urls:{}'.format(batch_id, urls))
            for i in range(0, len(urls)):
                with open(file_path[i], 'rb') as f:
                    res_upload = requests.put(urls[i], data=f)
                    if res_upload.status_code == 200:
                        print(f"{urls[i]} upload success")
                    else:
                        print(f"{urls[i]} upload failed")
        else:
            print('apply upload url failed,reason:{}'.format(result["msg"]))
    else:
        print('response not success. status:{} ,result:{}'.format(response.status_code, response))
except Exception as err:
    print(err)
```

### 请求体参数说明

| 参数 | 类型 | 是否必选 | 示例 | 描述 |
|------|------|----------|------|------|
| `enable_formula` | `bool` | 否 | `true` | 是否开启公式识别，默认 `true`，仅对 `pipeline`、`vlm` 模型有效。特别注意的是：对于 `vlm` 模型，这个参数只会影响行内公式的解析 |
| `enable_table` | `bool` | 否 | `true` | 是否开启表格识别，默认 `true`，仅对 `pipeline`、`vlm` 模型有效 |
| `language` | `string` | 否 | `ch` | 指定文档语言，默认 `ch`。可选值见 language 取值参考。仅对 `pipeline`、`vlm` 模型有效 |
| `file.url` | `string` | 是 | `demo.pdf` | 文件链接，支持 `.pdf`、`.doc`、`.docx`、`.ppt`、`.pptx`、`.xls`、`.xlsx`、图片（`png`/`jpg`/`jpeg`/`jp2`/`webp`/`gif`/`bmp`）、`.html` 多种格式 |
| `file.is_ocr` | `bool` | 否 | `true` | 是否启动 OCR 功能，默认 `false`，仅对 `pipeline`、`vlm` 模型有效 |
| `file.data_id` | `string` | 否 | `abc**` | 解析对象对应的数据 ID。由大小写英文字母、数字、下划线（`_`）、短划线（`-`）、英文句号（`.`）组成，不超过 128 个字符，可以用于唯一标识您的业务数据 |
| `file.page_ranges` | `string` | 否 | `1-200` | 指定页码范围，格式为逗号分隔的字符串。例如：`"2,4-6"`：表示选取第2页、第4页至第6页（包含4和6，结果为 [2,4,5,6]）；`"2--2"`：表示从第2页一直选取到倒数第二页（其中 `"-2"` 表示倒数第二页） |
| `callback` | `string` | 否 | `http://127.0.0.1/callback` | 解析结果回调通知您的 URL，支持使用 HTTP 和 HTTPS 协议的地址。该字段为空时，您必须定时轮询解析结果。callback 接口必须支持 POST 方法、UTF-8 编码、`Content-Type: application/json` 传输数据，以及参数 `checksum` 和 `content`。解析接口按照以下规则和格式设置 `checksum` 和 `content`，调用您的 callback 接口返回检测结果。<br><br>**checksum**：字符串格式，由用户 uid + seed + content 拼成字符串，通过 SHA256 算法生成。用户 UID 可在个人中心查询。为防篡改，您可以在获取到推送结果时，按上述算法生成字符串，与 checksum 做一次校验。<br><br>**content**：JSON 字符串格式，请自行解析反转成 JSON 对象。关于 content 结果的示例，请参见任务查询结果的返回示例，对应任务查询结果的 data 部分。<br><br>**说明**：您的服务端 callback 接口收到 Mineru 解析服务推送的结果后，如果返回的 HTTP 状态码为 200，则表示接收成功，其他的 HTTP 状态码均视为接收失败。接收失败时，Mineru 将最多重复推送 5 次检测结果，直到接收成功。重复推送 5 次后仍未接收成功，则不再推送，建议您检查 callback 接口的状态 |
| `seed` | `string` | 否 | `abc**` | 随机字符串，该值用于回调通知请求中的签名。由英文字母、数字、下划线（`_`）组成，不超过 64 个字符。由您自定义，用于在接收到内容安全的回调通知时校验请求由 Mineru 解析服务发起。<br><br>**说明**：当使用 `callback` 时，该字段必须提供 |
| `extra_formats` | `[string]` | 否 | `["docx","html"]` | `markdown`、`json` 为默认导出格式，无须设置。该参数仅支持 `docx`、`html`、`latex` 三种格式中的一个或多个。对源文件为 `html` 的文件无效 |
| `model_version` | `string` | 否 | `vlm` | Mineru 模型版本，三个选项：`pipeline`、`vlm`、`MinerU-HTML`，默认 `pipeline`。如果解析的是 HTML 文件，`model_version` 需明确指定为 `MinerU-HTML`；如果是非 HTML 文件，可选择 `pipeline` 或 `vlm` |
| `no_cache` | `bool` | 否 | `false` | 是否绕过缓存，默认 `false`。我们的 API 服务器会将 URL 内容缓存一段时间，设置为 `true` 可忽略缓存结果，从 URL 获取最新内容 |
| `cache_tolerance` | `int` | 否 | `900` | 缓存容忍时间（秒），默认 `900`（15分钟）。可容忍的 URL 内容缓存有效时间，超出该时间的缓存不会被使用。当 `no_cache` 为 `false` 时有效 |

### 响应参数说明

| 参数 | 类型 | 示例 | 说明 |
|------|------|------|------|
| `code` | `int` | `0` | 接口状态码，成功：`0` |
| `msg` | `string` | `ok` | 接口处理信息，成功：`"ok"` |
| `trace_id` | `string` | `c876cd60b202f2396de1f9e39a1b0172` | 请求 ID |
| `data.batch_id` | `string` | `2bb2f0ec-a336-4a0a-b61a-****` | 批量提取任务 id，可用于批量查询解析结果 |

## 批量获取任务结果
### 接口说明

通过 batch_id 批量查询提取任务的进度。

### Python 请求示例

```python
import requests

token = "API管理页面自定创建的token"
batch_id = "上一步批量提交返回的 batch_id"
url = f"https://mineru.net/api/v4/extract-results/batch/{batch_id}"
header = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}

res = requests.get(url, headers=header)
print(res.status_code)
print(res.json())
print(res.json()["data"])
```

### 响应参数说明

| 参数 | 类型 | 示例 | 说明 |
|------|------|------|------|
| `code` | `int` | `0` | 接口状态码，成功：`0` |
| `msg` | `string` | `ok` | 接口处理信息，成功：`"ok"` |
| `trace_id` | `string` | `c876cd60b202f2396de1f9e39a1b0172` | 请求 ID |
| `data.batch_id` | `string` | `2bb2f0ec-a336-4a0a-b61a-241afaf9cc87` | 批量提取任务 id |
| `data.extract_result.file_name` | `string` | `demo.pdf` | 文件名 |
| `data.extract_result.state` | `string` | `done` | 任务处理状态：<br>• `done` — 完成<br>• `waiting-file` — 等待文件上传排队提交解析任务中<br>• `pending` — 排队中<br>• `running` — 正在解析<br>• `failed` — 解析失败<br>• `converting` — 格式转换中 |
| `data.extract_result.full_zip_url` | `string` | `https://cdn-mineru.openxlab.org.cn/pdf/018e53ad-d4f1-475d-b380-36bf24db9914.zip` | 文件解析结果压缩包。非 HTML 文件解析结果详细说明请参考：[MinerU 输出文件说明](https://opendatalab.github.io/MinerU/reference/output_files/)。其中：<br>• `layout.json` — 中间处理结果（`middle.json`）<br>• `**_model.json` — 模型推理结果（`model.json`）<br>• `**_content_list.json` — 内容列表（`content_list.json`）<br>• `full.md` — MarkDown 解析结果<br><br>HTML 文件解析结果略有不同：<br>• `full.md` — MarkDown 解析结果<br>• `main.html` — 提取后正文 HTML |
| `data.extract_result.err_msg` | `string` | `文件格式不支持，请上传符合要求的文件类型` | 解析失败原因，当 `state=failed` 时有效 |
| `data.extract_result.data_id` | `string` | `abc**` | 解析对象对应的数据 ID。<br><br>**说明**：如果在解析请求参数中传入了 `data_id`，则此处返回对应的 `data_id` |
| `data.extract_result.extract_progress.extracted_pages` | `int` | `1` | 文档已解析页数，当 `state=running` 时有效 |
| `data.extract_result.extract_progress.start_time` | `string` | `2025-01-20 11:43:20` | 文档解析开始时间，当 `state=running` 时有效 |
| `data.extract_result.extract_progress.total_pages` | `int` | `2` | 文档总页数，当 `state=running` 时有效 |

### 响应示例

```json
{
  "code": 0,
  "data": {
    "batch_id": "2bb2f0ec-a336-4a0a-b61a-241afaf9cc87",
    "extract_result": [
      {
        "file_name": "example.pdf",
        "state": "done",
        "err_msg": "",
        "full_zip_url": "https://cdn-mineru.openxlab.org.cn/pdf/018e53ad-d4f1-475d-b380-36bf24db9914.zip"
      },
      {
        "file_name": "demo.pdf",
        "state": "running",
        "err_msg": "",
        "extract_progress": {
          "extracted_pages": 1,
          "total_pages": 2,
          "start_time": "2025-01-20 11:43:20"
        }
      }
    ]
  },
  "msg": "ok",
  "trace_id": "c876cd60b202f2396de1f9e39a1b0172"
}
```

## 常见错误码

| 错误码 | 说明 | 解决建议 |
|--------|------|----------|
| `A0202` | Token 错误 | 检查 Token 是否正确，请检查是否有 Bearer 前缀或者更换新 Token |
| `A0211` | Token 过期 | 更换新 Token |
| `-500` | 传参错误 | 请确保参数类型及 Content-Type 正确 |
| `-10001` | 服务异常 | 请稍后再试 |
| `-10002` | 请求参数错误 | 检查请求参数格式 |
| `-60001` | 生成上传 URL 失败，请稍后再试 | 请稍后再试 |
| `-60002` | 获取匹配的文件格式失败 | 检测文件类型失败，请确保请求的文件名及链接中带有正确的后缀名，且文件为 `pdf`、`doc`、`docx`、`ppt`、`pptx`、`xls`、`xlsx`、`png`、`jp(e)g` 中的一种 |
| `-60003` | 文件读取失败 | 请检查文件是否损坏并重新上传 |
| `-60004` | 空文件 | 请上传有效文件 |
| `-60005` | 文件大小超出限制 | 检查文件大小，最大支持 200MB |
| `-60006` | 文件页数超过限制 | 请拆分文件后重试 |
| `-60007` | 模型服务暂时不可用 | 请稍后重试或联系技术支持 |
| `-60008` | 文件读取超时 | 检查 URL 是否可访问 |
| `-60009` | 任务提交队列已满 | 请稍后再试 |
| `-60010` | 解析失败 | 请稍后再试 |
| `-60011` | 获取有效文件失败 | 请确保文件已上传 |
| `-60012` | 找不到任务 | 请确保 `task_id` 有效且未删除 |
| `-60013` | 没有权限访问该任务 | 只能访问自己提交的任务 |
| `-60014` | 删除运行中的任务 | 运行中的任务暂不支持删除 |
| `-60015` | 文件转换失败 | 可以手动转为 PDF 再上传 |
| `-60016` | 文件转换失败 | 文件转换为指定格式失败，可以尝试其他格式导出或重试 |
| `-60017` | 重试次数达到上限 | 等后续模型升级后重试 |
| `-60018` | 每日解析任务数量已达上限 | 明日再来 |
| `-60019` | HTML 文件解析额度不足 | 明日再来 |
| `-60020` | 文件拆分失败 | 请稍后重试 |
| `-60021` | 读取文件页数失败 | 请稍后重试 |
| `-60022` | 网页读取失败 | 可能因网络问题或限频导致读取失败，请稍后重试 |