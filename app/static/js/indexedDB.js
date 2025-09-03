let db = null;
const DB_NAME = 'destajos';
const DB_VERSION = 2; // 👈 subimos versión para forzar recreación
const STORE_QUEUE = 'queue';
const STORE_EMPLEADOS = 'GH_Empleados';
const STORE_DESTAJOS = 'GH_Destajos';
const STORE_USUARIOS = 'users';

function initDB(){
  return new Promise((resolve, reject) => {
    let request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = (event) => {
      console.error("❌ Error abriendo DB:", event.target.error);
      reject(event.target.error);
    }
    request.onsuccess = (event) => {
      db = event.target.result;
      console.log("✅ Base de datos abierta:", db.name);
      resolve(db);
    };
    request.onupgradeneeded = (event) => {
      db = event.target.result;

      // --- Store queue (pendientes de sincronización) ---
      if (!db.objectStoreNames.contains(STORE_QUEUE)) {
        db.createObjectStore(STORE_QUEUE, { keyPath: 'local_id', autoIncrement: true });
        console.log("🗂️ Store creada:", STORE_QUEUE);
      }

      // --- Store usuarios (para login offline) ---
      if (!db.objectStoreNames.contains(STORE_USUARIOS)) {
        db.createObjectStore(STORE_USUARIOS, { keyPath: "id" });
        console.log("🗂️ Store creada:", STORE_USUARIOS);
      }

      // --- Store empleados ---
      if (!db.objectStoreNames.contains(STORE_EMPLEADOS)) {
        db.createObjectStore(STORE_EMPLEADOS, { keyPath: "numeroDocumento" });
        console.log("🗂️ Store creada:", STORE_EMPLEADOS);
      }

      // --- Store destajos ---
      if (!db.objectStoreNames.contains(STORE_DESTAJOS)) {
        db.createObjectStore(STORE_DESTAJOS, { keyPath: "Id" });
        console.log("🗂️ Store creada:", STORE_DESTAJOS);
      }
    }
  })
}

function normalizarParaUI(r) {
  // Asegura un id de UI estable para x-for (no se usa para IndexedDB)
  if (r.local_id != null && (r.id == null || String(r.id).startsWith("local-"))) {
    r.id = `local-${r.local_id}`;
  }
  // evita que quede pegado en edición cuando recargues
  if (r._edit) r._edit = false;
  return r;
}

async function idbAdd(db, store, value) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    const req = tx.objectStore(store).add(value); // devuelve el local_id autoincrement
    req.onsuccess = (e) => resolve(e.target.result); // ← local_id numérico
    req.onerror   = (e) => reject(e.target.error);
  });
}

async function idbGetAll(db, store) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readonly");
    const req = tx.objectStore(store).getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror   = (e) => reject(e.target.error);
  });
}

async function idbClear(db, store) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, 'readwrite');
    tx.objectStore(store).clear();
    tx.oncomplete = () => resolve(true);
    tx.onerror = (e) => reject(e);
  });
}

async function idbPut(db, store, value) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    const req = tx.objectStore(store).put(value); // requiere value.local_id ya seteado
    req.onsuccess = () => resolve(true);
    req.onerror   = (e) => reject(e.target.error);
  });
}

async function idbDelete(db, store, key) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    const req = tx.objectStore(store).delete(key); // key === local_id (number)
    req.onsuccess = () => resolve(true);
    req.onerror   = (e) => reject(e.target.error);
  });
}

const API = {
  async get(url){
    try {
      const r = await fetch(url, { credentials:'same-origin' });
      if(!r.ok) {
        const text = await r.text();
        throw new Error(`Error API GET ${url}: ${r.status} ${r.statusText} - ${text}`);
      }
      return r.json();
    } catch(e){
      // Si fetch falla por conexión offline u otro error
      throw new Error(`Error API GET ${url}: ${e.message}`);
    }
  },
  async post(url, data){
    try {
      const r = await fetch(url, {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        credentials:'same-origin',
        body: JSON.stringify(data)
      });
      if(!r.ok) {
        const text = await r.text();
        throw new Error(`Error API POST ${url}: ${r.status} ${r.statusText} - ${text}`);
      }
      return r.json();
    } catch(e){
      throw new Error(`Error API POST ${url}: ${e.message}`);
    }
  },
  async put(url, data){
    try {
      const r = await fetch(url, {
        method:'PUT',
        headers:{'Content-Type':'application/json'},
        credentials:'same-origin',
        body: JSON.stringify(data)
      });
      if(!r.ok) {
        const text = await r.text();
        throw new Error(`Error API PUT ${url}: ${r.status} ${r.statusText} - ${text}`);
      }
      return r.json();
    } catch(e){
      throw new Error(`Error API PUT ${url}: ${e.message}`);
    }
  },
  async del(url){
    try {
      const r = await fetch(url, { method:'DELETE', credentials:'same-origin' });
      if(!r.ok) {
        const text = await r.text();
        throw new Error(`Error API DELETE ${url}: ${r.status} ${r.statusText} - ${text}`);
      }
      return r.json();
    } catch(e){
      throw new Error(`Error API DELETE ${url}: ${e.message}`);
    }
  }
};

function todayISO(){
  const d = new Date();
  const m = String(d.getMonth()+1).padStart(2,'0');
  const day = String(d.getDate()).padStart(2,'0');
  return `${d.getFullYear()}-${m}-${day}`;
}

// ==============================
// Alpine data: Formulario destajos
// ==============================
window.destajosForm = function(){
  return {
    empleados: [],
    destajos: [],
    empleado_nombre: '',
    empleado_documento: '',
    destajo_text: '',
    destajo_id: null,
    cantidad: 1,
    fecha: todayISO(),
    status: '',
    errores: {},   // 👈 aquí guardamos los errores

     async init() {
      // Detecta si hay internet o no
      if (navigator.onLine) {
        this.empleados = await fetch('/api/empleados').then(r => r.json());
        this.destajos = await fetch('/api/mdestajos').then(r => r.json());
      } else {
        const db = await openIndexedDB(); // tu función que abre IndexedDB
        this.empleados = await idbGetAll(db, 'GH_Empleados');
        this.destajos = await idbGetAll(db, 'GH_Destajos');
      }
    },

    asignarDocumento() {
      if (!this.empleado_nombre) {  
        this.empleado_documento = '';
        return;
      }

      const e = this.empleados.find(x => {
        if (!x.nombreCompleto || !x.apellidoCompleto) return false;
        const fullName = `${x.nombreCompleto} ${x.apellidoCompleto}`.trim().toLowerCase();
        return fullName === this.empleado_nombre.trim().toLowerCase();
      });

      this.empleado_documento = e ? e.numeroDocumento : '';
    },

    validar() {
      this.errores = {};
      if (!this.empleado_nombre.trim()) this.errores.empleado_nombre = "Debe seleccionar un empleado.";
      if (!this.empleado_documento.trim()) this.errores.empleado_documento = "No se asignó documento al empleado.";
      if (!this.destajo_id) this.errores.destajo = "Debe seleccionar un destajo válido.";
      if (!this.cantidad || this.cantidad < 1) this.errores.cantidad = "La cantidad debe ser mayor o igual a 1.";
      if (!this.fecha) this.errores.fecha = "Debe seleccionar una fecha.";
      return Object.keys(this.errores).length === 0;
    },

    async buscarEmpleado() {
      console.log("🔍 Buscando Empleado:", this.empleado_nombre);

      const q = this.empleado_nombre || this.empleado_documento;
      if (!q || q.length < 2) return;

      try {
        const res = await fetch(`/api/employees?q=${encodeURIComponent(q)}`);
        if (!res.ok) throw new Error("HTTP error " + res.status);
        const data = await res.json();
        
        if (Array.isArray(data)){
          this.empleados = data;

          const seleccionado = data.find(e =>
            e.nombre?.trim().toLowerCase() === this.empleado_nombre?.trim().toLowerCase()
          );

          if (seleccionado) {
            this.empleado_documento = seleccionado.documento;
          }
        } else {
          console.warn("⚠️ Respuesta inesperada de /api/employees:", data);
          this.empleados = [];
        }
        
      } catch (err) {
        console.error("⚠️ Error buscando empleado", err);
        this.status = "Error al buscar empleado";
      }
    },

    asignarDestajo() {
        // Busca en la lista de destajos por el texto ingresado
        const d = this.destajos.find(x => x.Concepto.toLowerCase() === this.destajo_text.trim().toLowerCase());
        this.destajo_id = d ? d.Id : null;  // <-- Aquí se asigna destajo_id
    },

    async searchDestajo(){
      const q = this.destajo_text;
      if(!q || q.length < 2) return;
      try {
        this.destajos = await API.get('/api/destajos?q='+encodeURIComponent(q));
        const hit = this.destajos.find(d => d.concepto === this.destajo_text);
        if(hit){ this.destajo_id = hit.id; }
      } catch(e){}
    },

    async submit() {
      if(!this.validar()){ this.status="Corrige errores"; return; }
      const payload = {
        empleado_documento: this.empleado_documento,
        empleado_nombre: this.empleado_nombre,
        destajo_id: this.destajo_id,
        cantidad: this.cantidad,
        fecha: this.fecha,
        _edit: false
      };

      const db = await initDB();
      if(navigator.onLine){
        try {
          await API.post('/api/registros', payload);
          this.status = 'Guardado en servidor';
        } catch(e){
          this.status = 'Error servidor, encolado offline';
          await idbAdd(db, STORE_QUEUE, payload);
        }
      } else {
        await idbAdd(db, STORE_QUEUE, payload);
        this.status = 'Guardado offline (pendiente de sincronizar)';
      }
    }
  }
}

function normalizarRegistro(r) {
  // si no tiene ninguna clave → le asignamos un local_id único
  if (!r.local_id && !r.id) {
    r.local_id = "local-" + crypto.randomUUID();
  }
  return r;
}

window.onload = async () => {
  const db = await initDB();
  const offline = await idbGetAll(db, STORE_QUEUE);
  this.registros = offline.map(x => normalizarParaUI(x));
};

// ==============================
// Alpine data: Vista consultar
// ==============================
window.consultarView = function(){
  return {
    documento: '',
    desde: '',
    hasta: '',
    registros: [],
    destajos: [],
    destajosMap: new Map(),
    backup: new Map(),
    ready: false,

    // Inicializar destajos
    async init() {
      try {
        // 1️⃣ Inicializar fechas por defecto
        const today = new Date();
        this.desde = today.toISOString().split('T')[0]; // hoy
        this.hasta = today.toISOString().split('T')[0]; // hoy

        // 2️⃣ Cargar destajos
        const d = await API.get("/api/destajos");
        this.destajos = d;
        // Forzar claves numéricas
        d.forEach(x => this.destajosMap.set(Number(x.id), x.concepto));
        this.ready = true;

        this.buscar();

        console.log("🟢 Destajos cargados:", this.destajos);  // <--- aquí
      } catch (e) {
        console.error("No se pudieron cargar los destajos", e);
      }
    },

    async buscar() {
      if (!this.ready) return;

      const p = new URLSearchParams();
      if(this.documento) p.set('documento', this.documento);
      if(this.desde) p.set('desde', this.desde);
      if(this.hasta) p.set('hasta', this.hasta);

      if (navigator.onLine) {
        try {
          this.registros = await API.get('/api/registros?' + p.toString());
          this.registros.forEach(r => r.destajo_id = Number(r.destajo_id));
          return;
        } catch (e) {
          console.warn("⚠️ Backend dio error, uso cache local", e);
        }
      } else {
        console.log("🌐 Sin conexión → voy directo a cache local");
      }

      // --- OFFLINE fallback ---
      try {
        const db = await initDB();
        const offline = await idbGetAll(db, STORE_QUEUE);

        this.registros = offline.map(r => {
          r._isOffline = true;
          r.id = r.id ?? `local-${r.local_id}`; // clave única para Alpine
          return normalizarParaUI(r);
        });

      } catch (e) {
        console.error("❌ Error cargando IndexedDB", e);
        this.registros = [];
      }
    },

    editar(r) {
      // Guardamos copia del registro para posible cancelación
      this.backup.set(r.id, JSON.parse(JSON.stringify(r)));

      // Función que activa edición y asigna valor
      const activarEdicion = () => {
        r._edit = true; // activar el select
        this.$nextTick(() => {
          // Forzamos que r.destajo_id sea un número y coincida con las opciones
          r.destajo_id = Number(r.destajo_id);
          console.log("✅ Editando registro:", r.id, "destajo_id:", r.destajo_id);
        });
      };

      // Si la lista aún no está cargada
      if (!this.destajos || this.destajos.length === 0) {
        console.log("⏳ Destajos no cargados, esperando...");
        this.loadDestajos().then(() => {
          activarEdicion(); // activamos edición una vez cargados
        });
      } else {
        activarEdicion(); // si ya están cargados, activamos de inmediato
      }
    },

    async loadDestajos() {
      const data = await fetch('/api/destajos').then(r => r.json());
      this.destajos = data;
    },

    cancelar(r){
      const orig = this.backup.get(r.id);
      if(orig){
        Object.assign(r, orig);
        this.backup.delete(r.id);
      }
      r._edit = false;
      this.registros = [...this.registros]; // actualizar fila
    },

    // ==================== GUARDAR (online + offline) ====================
    async guardar(r) {
      // --- Validación ---
      if (!r.fecha) { alert("⚠️ Debe ingresar una fecha."); return; }
      if (!r.cantidad || Number(r.cantidad) < 1) { alert("⚠️ La cantidad debe ser mayor o igual a 1."); return; }
      if (!r.destajo_id || Number(r.destajo_id) <= 0) { alert("⚠️ Debe seleccionar un destajo válido."); return; }

      const payload = {
        fecha: r.fecha,
        cantidad: Number(r.cantidad),
        destajo_id: Number(r.destajo_id),
      };

      // --- ONLINE ---
      if (navigator.onLine && r.id && !String(r.id).startsWith("local-")) {
        try {
          await API.put(`/api/registros/${r.id}`, payload);

          r._edit = false;
          this.backup.set(r.id, JSON.parse(JSON.stringify(r)));
          this.registros = [...this.registros];
          console.log("✅ Registro actualizado en servidor", r);
          return;
        } catch (e) {
          console.warn("⚠️ Error servidor, guardando en cola offline", e);
        }
      }

      // --- OFFLINE / FALLBACK ---
      try {
        const db = await initDB();

        // Clon limpio para IndexedDB (evita DataCloneError)
        const clean = JSON.parse(JSON.stringify({ ...r, ...payload }));

        r._edit = false;
        if (clean.local_id != null) {
          // update en cola (ya debe traer local_id numérico)
          await idbPut(db, STORE_QUEUE, clean);
          console.log("💾 Actualizado en cola local:", clean);
        } else {
          // insert nuevo → dejamos que IDB genere local_id (numérico)
          const newLocalId = await idbAdd(db, STORE_QUEUE, clean);
          r.local_id = newLocalId;       // reflejar en UI
          r.id = `local-${newLocalId}`;  // id de UI estable (no se usa para IDB)
          console.log("💾 Guardado nuevo en cola local:", { ...clean, local_id: newLocalId });
        }
        this.registros = this.registros.map(x => x === r ? normalizarParaUI(r) : normalizarParaUI(x));
        alert("✅ Guardado offline (pendiente de sincronizar)");
      } catch (e) {
        console.error("❌ Error guardando en IndexedDB", e);
        alert("Error guardando en modo offline");
      }
    },

    // ==================== ELIMINAR (online + offline) ====================
    async eliminar(target) {
      if (!confirm("¿Eliminar registro?")) return;

      // 1) Normaliza el parámetro a objeto `r`
      let r = target;
      if (typeof target !== "object") {
        r = this.registros.find(
          (x) => String(x.id) === String(target) || String(x.local_id) === String(target)
        );
      }
      if (!r) {
        console.error("❌ No se encontró el registro a eliminar:", target);
        return;
      }

      // 2) Si está online y tiene id de servidor válido → borra en backend
      if (navigator.onLine && r.id && !String(r.id).startsWith("local-")) {
        try {
          await API.del("/api/registros/" + r.id);
          this.registros = this.registros.filter((x) => x !== r);
          return;
        } catch (e) {
          console.warn("⚠️ No se pudo borrar en servidor, probando offline", e);
        }
      }

      // 3) OFFLINE: borrar de la cola usando SIEMPRE el keyPath del store (local_id numérico)
      try {
        const db = await initDB();

        const key = r.local_id; // ← CLAVE REAL DEL STORE
        if (key === null || key === undefined) {
          console.error("❌ Falta local_id, no se puede borrar offline", r);
          alert("Error eliminando offline: falta local_id");
          return;
        }

        await idbDelete(db, STORE_QUEUE, key);

        // Quita de la UI comparando por local_id (no por id string)
        this.registros = this.registros.filter((x) => String(x.local_id) !== String(key));

        console.log("🗑️ Eliminado de cola local:", r);
      } catch (e) {
        console.error("❌ Error borrando de IndexedDB", e);
        alert("Error eliminando offline");
      }
    }
  }
}

// Inicializa la primera sincronización
// trySync();

// Registrar Alpine
document.addEventListener('alpine:init', () => {
  Alpine.data('consultarView', consultarView);
  Alpine.data('destajosForm', destajosForm);
});


// ==============================
// Sync offline → server
// ==============================
async function trySync(){
  if(!navigator.onLine) return;
  const db = await initDB();
  const items = await idbGetAll(db, STORE_QUEUE);
  if(items.length === 0) return;
  const payload = items.map(({local_id, ...rest})=>rest);
  try {
    await API.post('/api/sync', payload);
    await idbClear(db, STORE_QUEUE);
    console.log('✅ Sincronizado', payload.length);
  } catch(e){
    console.warn('⚠️ Sync fallo', e);
  }
}

window.addEventListener('online', trySync);
document.addEventListener('visibilitychange', ()=> {
  if(document.visibilityState === 'visible') trySync();
});

// Inicializa la primera sincronización
trySync();

// Registrar Alpine
document.addEventListener('alpine:init', () => {
  Alpine.data('consultarView', consultarView);
  Alpine.data('destajosForm', destajosForm);
});

async function handleLogin() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    // Llama primero loginOnline, que caerá a loginOffline si no hay conexión
    const success = await loginOnline(username, password);

    if(success){
        console.log("Usuario logueado:", getCurrentUser());
        // Redirigir a la app o actualizar UI
        window.location.href = "/"; 
    } else {
        console.log("Login fallido");
    }
}

function getCurrentUser() {
    const user = localStorage.getItem('currentUser');
    return user ? JSON.parse(user) : null;
}

// Verificar si hay usuario logueado
if(getCurrentUser()){
    console.log("Usuario logueado:", getCurrentUser().username);
} else {
    console.log("No hay usuario logueado");
}

async function loginOffline(username, password) {
    const db = await initDB();
    const usuarios = await idbGetAll(db, STORE_USUARIOS);

    const user = usuarios.find(u => u.username === username && u.password === password);
    if(user){
        localStorage.setItem('currentUser', JSON.stringify(user));
        return true;
    }
    return false;
}

async function loginOnline(username, password) {
    if(navigator.onLine){
        try {
            const res = await API.post('/api/login', { username, password });
            if(res.success){
                localStorage.setItem('currentUser', JSON.stringify(res.user));
                await syncTables(); // sincroniza tablas al loguearse
                return true;
            }
        } catch(e){
            console.warn('⚠️ Login online falló, probando offline', e);
        }
    }

    // fallback offline
    return await loginOffline(username, password);
}

window.addEventListener('load', async () => {
    await initDB();
    if(navigator.onLine){
        await syncTables();
    }
});

async function syncTables() {
    if (!navigator.onLine) return; // solo online
    const db = await initDB();

    try {
        // Traer usuarios
        let usuarios = [];
        try { usuarios = await API.get('/auth/users'); } 
        catch(e){ console.warn("⚠️ No se pudo sincronizar users", e); }

        // Traer empleados
        let empleados = [];
        try { empleados = await API.get('/api/empleados'); } 
        catch(e){ console.warn("⚠️ No se pudo sincronizar empleados", e); }

        // Traer destajos
        let destajos = [];
        try { destajos = await API.get('/api/mdestajos'); } 
        catch(e){ console.warn("⚠️ No se pudo sincronizar destajos", e); }

        // Limpiar e insertar solo lo que se trajo
        if(usuarios.length){
            await idbClear(db, STORE_USUARIOS);
            for(const u of usuarios) await idbAdd(db, STORE_USUARIOS, u);
        }

        if(empleados.length){
            await idbClear(db, STORE_EMPLEADOS);
            for(const e of empleados) await idbAdd(db, STORE_EMPLEADOS, e);
        }

        if(destajos.length){
            await idbClear(db, STORE_DESTAJOS);
            for(const d of destajos) await idbAdd(db, STORE_DESTAJOS, d);
        }

        console.log('✅ Tablas locales sincronizadas (las que pudieron cargarse)');

    } catch (e) {
        console.error('❌ Error general sincronizando tablas locales', e);
    }
}


window.initDB = initDB;
