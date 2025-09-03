document.addEventListener('DOMContentLoaded', async () => {
    await initDB();

    const session = await getValidSession();

    if (!session) {
        // No hay token válido → redirigir al login
        window.location.href = "/login";
    } else {
        console.log("✅ Sesión válida:", session.user);
        // Aquí puedes cargar datos offline si quieres
    }
});
