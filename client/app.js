(() => {
  const API = "http://localhost:8002";
  const main = document.getElementById("main");

  function getToken() {
    return localStorage.getItem("token");
  }
  function authHeaders() {
    return { "Authorization": "Bearer " + getToken() };
  }

  function showError(container, msg) {
    container.querySelectorAll(".error").forEach(e => e.remove());
    const div = document.createElement("div");
    div.className = "error";
    div.textContent = msg;
    container.appendChild(div);
  }

  async function render() {
    if (!getToken()) {
      renderAuth();
    } else {
      await renderFiles();
    }
  }

  // --- Авторизация ---
  function renderAuth() {
    main.innerHTML = "";
    const div = document.createElement("div");
    div.className = "auth";

    div.innerHTML = `
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
    main.appendChild(div);

    document.getElementById("btn-register").onclick = async () => {
      showError(div, "");
      try {
        const res = await fetch(API + "/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: document.getElementById("up-email").value,
            password: document.getElementById("up-pass").value,
          }),
        });
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || "Ошибка регистрации");
        }
        alert("Регистрация успешна. Войдите, пожалуйста.");
      } catch (err) {
        showError(div, err.message);
      }
    };

    document.getElementById("btn-login").onclick = async () => {
      showError(div, "");
      try {
        const res = await fetch(API + "/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: document.getElementById("in-email").value,
            password: document.getElementById("in-pass").value,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Ошибка входа");
        localStorage.setItem("token", data.access_token);
        await render();
      } catch (err) {
        showError(div, err.message);
      }
    };
  }

  // --- Файловый менеджер ---
  async function renderFiles() {
    main.innerHTML = "";
    const div = document.createElement("div");
    div.className = "files";

    // Кнопка выход
    const btnOut = document.createElement("button");
    btnOut.textContent = "Выйти";
    btnOut.onclick = () => {
      localStorage.removeItem("token");
      render();
    };
    div.appendChild(btnOut);

    // Раздел загрузки
    const upDiv = document.createElement("div");
    upDiv.className = "upload-section";
    const inp = document.createElement("input");
    inp.type = "file";
    const btnUp = document.createElement("button");
    btnUp.textContent = "Загрузить";
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
        if (!res.ok) throw new Error("Ошибка загрузки");
        await refreshList(listUl);
        await renderStats(statsDiv);
      } catch (err) {
        showError(upDiv, err.message);
      }
    };
    upDiv.append(inp, btnUp);
    div.appendChild(upDiv);

    // Список файлов
    const listUl = document.createElement("ul");
    listUl.className = "file-list";
    div.appendChild(listUl);

    // Статистика
    const statsDiv = document.createElement("div");
    statsDiv.className = "stats";
    div.appendChild(statsDiv);

    main.appendChild(div);

    await refreshList(listUl);
    await renderStats(statsDiv);
  }

  async function refreshList(container) {
    container.innerHTML = "";
    try {
      const res = await fetch(API + "/files/", { headers: authHeaders() });
      if (!res.ok) throw new Error("Не удалось получить файлы");
      const list = await res.json();
      list.forEach((file) => {
        const li = document.createElement("li");
        li.className = "file-item";
        const name = document.createElement("div");
        name.className = "filename";
        name.textContent = file;

        const actions = document.createElement("div");
        actions.className = "file-actions";

        const btnDl = document.createElement("button");
        btnDl.textContent = "📥";
        btnDl.onclick = () => downloadFile(file);

        const btnLink = document.createElement("button");
        btnLink.textContent = "🔗";
        btnLink.onclick = () => getPublicLink(file);

        const btnDel = document.createElement("button");
        btnDel.textContent = "🗑️";
        btnDel.onclick = () => deleteFile(file, container);

        actions.append(btnDl, btnLink, btnDel);
        li.append(name, actions);
        container.appendChild(li);
      });
    } catch (err) {
      showError(container, err.message);
    }
  }

  async function renderStats(container) {
    try {
      const res = await fetch(API + "/files/stats", { headers: authHeaders() });
      if (!res.ok) throw new Error("Не удалось получить статистику");
      const data = await res.json();
      container.textContent = `Всего файлов: ${data.total_files}, общий размер: ${data.total_size} байт`;
    } catch (err) {
      showError(container, err.message);
    }
  }

  async function downloadFile(file) {
    try {
      const res = await fetch(
        API + "/files/download/" + encodeURIComponent(file),
        { headers: authHeaders() }
      );
      if (!res.ok) throw new Error("Ошибка скачивания");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = file;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.message);
    }
  }

  async function deleteFile(file, container) {
    if (!confirm(`Удалить ${file}?`)) return;
    try {
      const res = await fetch(
        API + "/files/" + encodeURIComponent(file),
        { method: "DELETE", headers: authHeaders() }
      );
      if (!res.ok) throw new Error("Не удалось удалить");
      await refreshList(container);
      await renderStats(container.parentNode.querySelector(".stats"));
    } catch (err) {
      alert(err.message);
    }
  }

  async function getPublicLink(file) {
    try {
      const res = await fetch(
        API + "/files/" + encodeURIComponent(file) + "/public-link",
        { method: "POST", headers: authHeaders() }
      );
      if (!res.ok) throw new Error("Ошибка ссылки");
      const data = await res.json();
      document.querySelectorAll(".public-link").forEach(e => e.remove());
      const linkBox = document.createElement("div");
      linkBox.className = "public-link";
      linkBox.innerHTML = `Публичная ссылка: <a href="${data.public_url}" target="_blank">${data.public_url}</a>`;
      document.getElementById("main").appendChild(linkBox);
    } catch (err) {
      alert(err.message);
    }
  }

  render();
})();
