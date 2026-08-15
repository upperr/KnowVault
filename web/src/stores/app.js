import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const loading = ref(false)
  const message = ref('')
  
  const setLoading = (value) => {
    loading.value = value
  }
  
  const setMessage = (value) => {
    message.value = value
  }
  
  return { loading, message, setLoading, setMessage }
})
