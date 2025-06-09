(() => {
  const API = "http://localhost:8002";
  const main = document.getElementById("main");
  let userId = null;
  let userPrefix = "";

  function getToken() {
    return localStorage.getItem("token");
  }
  function authHeaders() {
    return { "Authorization": "Bearer " + getToken() };
  }
  function showError(container, msg) {
    container.querySelectorAll(".error").forEach(e => e.remove());
    if (!msg) return;
    const div = document.createElement("div");
    div.className = "error";
    div.textContent = msg;
    container.appendChild(div);
  }

  async function render() {
    if (!getToken()) {
      renderAuth();
    } else {
      // получаем профиль
      try {
        const res = await fetch(API + "/auth/me", { headers: authHeaders() });
        if (!res.ok) throw new Error();
        const profile = await res.json();
        userId = profile.id;
        userPrefix = `user_${userId}`;
      } catch {
        localStorage.removeItem("token");
        return renderAuth();
      }
      await renderFiles();
    }
  }

  // --- Авторизация ---
  function renderAuth() {
    main.innerHTML = "";
    const d = document.createElement("div");
    d.className = "auth";
    d.innerHTML = `
      <h2>Вход / Регистрация</h2>
      <div class="auth-forms">
        <div>
          <h3>Вход</h3>
          <input id="in-email" placeholder="Email">
          <input id="in-pass" type="password" placeholder="Пароль">
          <button id="btn-login">Войти</button>
        </div>
        <div>
          <h3>Регистрация</h3>
          <input id="up-email" placeholder="Email">
          <input id="up-pass" type="password" placeholder="Пароль">
          <button id="btn-register">Зарегистрироваться</button>
        </div>
      </div>
    `;
    main.appendChild(d);

    d.querySelector("#btn-register").onclick = async () => {
      showError(d, "");
      try {
        const res = await fetch(API + "/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: d.querySelector("#up-email").value,
            password: d.querySelector("#up-pass").value,
          }),
        });
        if (!res.ok) {
          const e = await res.json();
          throw new Error(e.detail || "Ошибка регистрации");
        }
        alert("Регистрация прошла успешно. Войдите.");
      } catch (e) {
        showError(d, e.message);
      }
    };

    d.querySelector("#btn-login").onclick = async () => {
      showError(d, "");
      try {
        const res = await fetch(API + "/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: d.querySelector("#in-email").value,
            password: d.querySelector("#in-pass").value,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Ошибка входа");
        localStorage.setItem("token", data.access_token);
        await render();
      } catch (e) {
        showError(d, e.message);
      }
    };
  }

  // --- Файловый менеджер ---
  async function renderFiles() {
    main.innerHTML = "";
    const div = document.createElement("div");
    div.className = "files";

    // Кнопка «Выйти»
    const btnOut = document.createElement("button");
    btnOut.textContent = "Выйти";
    btnOut.onclick = () => {
      localStorage.removeItem("token");
      userId = null;
      render();
    };
    div.appendChild(btnOut);

    // Секция загрузки
    const upDiv = document.createElement("div");
    upDiv.className = "upload-section";
    const inp = document.createElement("input"); inp.type = "file";
    const btnUp = document.createElement("button"); btnUp.textContent = "Загрузить";
    btnUp.onclick = async () => {
      showError(upDiv, "");
      if (!inp.files[0]) return showError(upDiv, "Выберите файл");
      const fd = new FormData();
      fd.append("file", inp.files[0]);
      try {
        const res = await fetch(API + "/files/upload", {
          method: "POST",
          headers: authHeaders(),
          body: fd,
        });
        if (!res.ok) {
          const e = await res.json();
          throw new Error(e.detail || "Ошибка загрузки");
        }
        await refreshList(listUl);
        await renderStats(statsDiv);
        publicLinkDiv.style.display = "none";
      } catch (e) {
        showError(upDiv, e.message);
      }
    };
    upDiv.append(inp, btnUp);
    div.appendChild(upDiv);

    // Список и статистика
    const listUl = document.createElement("ul");
    listUl.className = "file-list";
    const statsDiv = document.createElement("div");
    statsDiv.className = "stats";

    // Блок для публичной ссылки
    const publicLinkDiv = document.createElement("div");
    publicLinkDiv.className = "public-link";
    publicLinkDiv.style.display = "none";  // прячем по умолчанию

    div.append(listUl, statsDiv, publicLinkDiv);
    main.appendChild(div);

    await refreshList(listUl);
    await renderStats(statsDiv);
  }

  // Получить и отрисовать список
  async function refreshList(container) {
    container.innerHTML = "";
    try {
      const res = await fetch(`${API}/files/`, {
        headers: authHeaders()
      });
      if (!res.ok) throw new Error("Не удалось получить список");
      const { files } = await res.json();

      files.forEach(name => {
        const fullPath = `${userPrefix}/${name}`;
        const li = document.createElement("li");
        li.className = "file-item";

        const nm = document.createElement("div");
        nm.className = "filename";
        nm.textContent = name;

        const acts = document.createElement("div");
        acts.className = "file-actions";

        const btnDl = document.createElement("button");
        btnDl.textContent = "📥";
        btnDl.onclick = () => downloadFile(fullPath);

        const btnPub = document.createElement("button");
        btnPub.textContent = "🔗";
        btnPub.onclick = () => getPublicLink(fullPath);

        const btnDel = document.createElement("button");
        btnDel.textContent = "🗑️";
        btnDel.onclick = () => deleteFile(fullPath, container);

        acts.append(btnDl, btnPub, btnDel);
        li.append(nm, acts);
        container.appendChild(li);
      });
    } catch (err) {
      showError(container, err.message);
    }
  }

  // Отрисовать статистику
  async function renderStats(container) {
    container.textContent = "";
    try {
      const res = await fetch(API + "/files/stats", {
        headers: authHeaders()
      });
      if (!res.ok) throw new Error("Не удалось получить статистику");
      const { total_files, total_size } = await res.json();
      container.textContent = `Всего файлов: ${total_files}, размер: ${total_size} байт`;
    } catch (err) {
      showError(container, err.message);
    }
  }

  // Скачивание
  async function downloadFile(fullPath) {
    try {
      const res = await fetch(
        `${API}/files/download/${encodeURIComponent(fullPath)}`,
        { headers: authHeaders() }
      );
      if (!res.ok) throw new Error("Ошибка скачивания");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fullPath.split("/").pop();
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(e.message);
    }
  }

  // Удаление
  async function deleteFile(fullPath, container) {
    if (!confirm(`Удалить ${fullPath.split("/").pop()}?`)) return;
    try {
      const res = await fetch(
        `${API}/files/${encodeURIComponent(fullPath)}`,
        { method: "DELETE", headers: authHeaders() }
      );
      if (!res.ok) throw new Error("Не удалось удалить");
      await refreshList(container);
      await renderStats(container.parentNode.querySelector(".stats"));
      // прячем прошлую ссылку
      container.parentNode.querySelector(".public-link").style.display = "none";
    } catch (e) {
      alert(e.message);
    }
  }

  // Публичная ссылка
  async function getPublicLink(fullPath) {
    const publicLinkDiv = document.querySelector(".public-link");
    publicLinkDiv.style.display = "none";
    try {
      const res = await fetch(
        `${API}/files/${encodeURIComponent(fullPath)}/public-link`,
        { method: "POST", headers: authHeaders() }
      );
      if (!res.ok) throw new Error("Ошибка ссылки");
      const { public_url } = await res.json();
      publicLinkDiv.innerHTML = `Публичная ссылка: <a href="${public_url}" target="_blank">${public_url}</a>`;
      publicLinkDiv.style.display = "block";
      publicLinkDiv.scrollIntoView({ behavior: "smooth" });
    } catch (e) {
      publicLinkDiv.innerHTML = `Ошибка получения ссылки: ${e.message}`;
      publicLinkDiv.style.display = "block";
    }
  }

  render();
})();
