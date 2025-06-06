// client/app.js

const API = "http://localhost:8002"

const app = Vue.createApp({
  data() {
    return {
      email: "",
      password: "",
      token: localStorage.token || "",
      authError: "",
      fileError: "",
      profile: {},
      files: [],
      stats: {},
      publicLinks: {},      // хранит публичные URL по имени файла
      publicLinkError: ""   // ошибка при запросе публичной ссылки
    }
  },
  created() {
    if (this.token) this.fetchAll()
  },
  methods: {
    async register() { await this.auth("/auth/register") },
    async login()    { await this.auth("/auth/login")    },

    async auth(path) {
      this.authError = ""
      try {
        const res = await fetch(API + path, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: this.email, password: this.password })
        })
        if (!res.ok) throw await res.json()
        const data = await res.json()
        this.token = data.access_token
        localStorage.token = this.token
        await this.fetchAll()
      } catch (e) {
        this.authError = e.detail || JSON.stringify(e)
      }
    },

    logout() {
      this.token = ""
      localStorage.removeItem("token")
      this.profile = {}
      this.files = []
      this.stats = {}
      this.publicLinks = {}
      this.publicLinkError = ""
    },

    authHeaders() {
      return { "Authorization": "Bearer " + this.token }
    },

    async fetchAll() {
      // получаем профиль
      const me  = await fetch(API + "/auth/me", { headers: this.authHeaders() })
      this.profile = await me.json()

      // получаем список файлов
      const fl  = await fetch(API + "/files/", { headers: this.authHeaders() })
      this.files = await fl.json()

      // получаем статистику
      const st = await fetch(API + "/files/stats", { headers: this.authHeaders() })
      this.stats = await st.json()

      // сбрасываем ранее сгенерированные ссылки (если были)
      this.publicLinks = {}
      this.publicLinkError = ""
    },

    async upload() {
      this.fileError = ""
      const file = this.$refs.f.files[0]
      if (!file) {
        this.fileError = "Выберите файл"
        return
      }

      const fd = new FormData()
      fd.append("file", file)

      const res = await fetch(API + "/files/upload", {
        method:  "POST",
        headers: this.authHeaders(),  // требует токен
        body:    fd
      })
      if (!res.ok) {
        const err = await res.json()
        this.fileError = err.detail || "Ошибка загрузки"
      }
      await this.fetchAll()
    },

    async download(name) {
      // приватное скачивание — остаётся fetch с Authorization
      this.fileError = ""
      try {
        const res = await fetch(
          `${API}/files/download/${encodeURIComponent(name)}`, {
            headers: this.authHeaders()
          }
        )
        if (!res.ok) {
          const err = await res.json()
          this.fileError = err.detail || "Ошибка при скачивании"
          return
        }
        const blob = await res.blob()
        const url  = URL.createObjectURL(blob)
        const a    = document.createElement("a")
        a.href     = url
        a.download = name
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
      } catch {
        this.fileError = "Ошибка при скачивании"
      }
    },

    async remove(name) {
      await fetch(`${API}/files/${encodeURIComponent(name)}`, {
        method:  "DELETE",
        headers: this.authHeaders()
      })
      await this.fetchAll()
    },

    async makePublicLink(name) {
      this.publicLinkError = ""

      try {
        // Приватный POST для генерации токена
        const res = await fetch(
          `${API}/files/${encodeURIComponent(name)}/public-link`,
          {
            method: "POST",
            headers: this.authHeaders()
          }
        )
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          this.publicLinkError = err.detail || "Ошибка при создании публичной ссылки"
          return
        }
        const data = await res.json()
        // data.public_url = например "http://localhost:8002/files/public/<token>"
        this.$set(this.publicLinks, name, data.public_url)
      } catch (e) {
        console.error("Ошибка при запросе публичной ссылки:", e)
        this.publicLinkError = "Сетевая ошибка при создании публичной ссылки"
      }
    }
  }
})

app.mount("#app")
