import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useChatStore = defineStore('chat', () => {
  // 聊天记录
  const chatHistory = ref([])
  // 当前检索到的文档片段
  const currentChunks = ref([])
  // 是否使用对话历史
  const useHistory = ref(true)

  // 添加消息
  const addMessage = (message) => {
    chatHistory.value.push(message)
  }

  // 更新消息（通过索引）
  const updateMessage = (index, updates) => {
    if (index >= 0 && index < chatHistory.value.length) {
      chatHistory.value[index] = { ...chatHistory.value[index], ...updates }
    }
  }

  // 清空历史
  const clearHistory = () => {
    chatHistory.value = []
    currentChunks.value = []
  }

  // 设置当前检索片段
  const setCurrentChunks = (chunks) => {
    currentChunks.value = chunks
  }

  // 设置是否使用历史
  const setUseHistory = (value) => {
    useHistory.value = value
  }

  // 初始化欢迎消息（仅在空的时候调用）
  const initWelcomeMessage = () => {
    if (chatHistory.value.length === 0) {
      chatHistory.value.push({
        role: 'assistant',
        content: '您好！我是本地文档智能问答助手。我可以基于您本地文件夹中的文档内容回答问题，支持跨文件整合信息、精准定位原文依据。请问有什么可以帮您？'
      })
    }
  }

  return {
    chatHistory,
    currentChunks,
    useHistory,
    addMessage,
    updateMessage,
    clearHistory,
    setCurrentChunks,
    setUseHistory,
    initWelcomeMessage
  }
})
