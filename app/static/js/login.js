document.addEventListener('DOMContentLoaded', async () => {
    await initDB();

    const form = document.getElementById('loginForm');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const username = document.getElementById("username").value.trim();
        const password = document.getElementById("password").value;

        if (!username || !password) { alert("Completa todos los campos"); return; }

        try {
            if (navigator.onLine) {
                // --- LOGIN ONLINE ---
                const res = await fetch("/auth/api/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username, password }),
                    credentials: "same-origin"
                });

                const data = await res.json();
                if (!res.ok || !data.success) { alert(data.message || "Usuario o contraseña incorrectos"); return; }

                // Guardar token en IndexedDB
                const issuedAt = Date.now();
                const expiresAt = issuedAt + 24*60*60*1000;
                await saveSession({ token: data.token, user: data.user, issuedAt, expiresAt });

                console.log("✅ Login online OK:", data.user);
                await precargarDatosOffline();
                window.location.href = "/";

            } else {
                // --- LOGIN OFFLINE ---
                const session = await getValidSession();
                if (session && session.user.username === username) {
                    console.log("✅ Login offline válido para:", username);
                    await precargarDatosOffline();
                    window.location.href = "/";
                } else {
                    alert("No se puede iniciar sesión offline");
                }
            }
        } catch (err) {
            console.error("❌ Error login:", err);
            alert("Error conectando con el servidor");
        }
    });

    async function precargarDatosOffline() {
        try {
            const empleados = await idbGetAll('GH_Empleados');
            const destajos = await idbGetAll('GH_Destajos');
            console.log("📦 Datos offline cargados", { empleados, destajos });
        } catch(e){ console.warn("⚠️ Error cargando datos offline", e); }
    }
});
