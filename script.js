// ==========================================
// 1. VARIABLES GLOBALES Y CARGA INICIAL
// ==========================================
let torneoData = null;

document.addEventListener("DOMContentLoaded", () => {
    cargarTorneo();
});

function formatearFechaEspanol(fechaStr) {
    if (!fechaStr) return "";
    const dias = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
    const meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
    
    const partes = fechaStr.split("-");
    const fecha = new Date(partes[0], partes[1] - 1, partes[2]);
    
    const nombreDia = dias[fecha.getDay()];
    const diaNum = fecha.getDate();
    const mesNombre = meses[fecha.getMonth()];
    const anio = fecha.getFullYear();
    
    return `${nombreDia}, ${diaNum} de ${mesNombre} de ${anio}`;
}

async function cargarTorneo() {
    try {
        const response = await fetch('/torneo_data.json'); 
        if (!response.ok) throw new Error("Error al obtener datos");
        torneoData = await response.json();
        actualizarInterfaz();
    } catch (error) {
        console.error("Fallo al cargar:", error);
    }
}

function actualizarInterfaz() {
    if (!torneoData) return;

    // Vistas Públicas
    renderizarPosiciones();
    renderizarResultadosYProximos();
    renderizarGoleadores();
    renderizarFaseFinal();
    
    // Vistas de Administración
    llenarSelectsEquipos();
    renderizarAdminEquipos(); // <--- NUEVA: Gestión de equipos
    renderizarAdminGoleadores();
    renderizarAdminPartidos();
    renderizarAdminFaseFinal();
}

// ==========================================
// 2. NAVEGACIÓN (TABS)
// ==========================================
function openTab(evt, tabName) {
    let i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tab-content");
    for (i = 0; i < tabcontent.length; i++) tabcontent[i].style.display = "none";
    
    tablinks = document.getElementsByClassName("tab-link");
    for (i = 0; i < tablinks.length; i++) tablinks[i].classList.remove("active");
    
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.classList.add("active");
}

// ==========================================
// 3. RENDERIZADO PÚBLICO (Tablas, Resultados, etc.)
// ==========================================

function renderizarPosiciones() {
    const container = document.getElementById("posiciones");
    if (!container) return;

    let stats = {};
    Object.values(torneoData.equipos).forEach(eq => {
        if (eq.grupo && eq.grupo !== "SIN GRUPO") {
            stats[eq.nombre] = { 
                nombre: eq.nombre, logo: eq.logo, grupo: eq.grupo, 
                PJ:0, G:0, E:0, P:0, GF:0, GC:0, DG:0, PTS:0 
            };
        }
    });

    torneoData.partidos.forEach(p => {
        if (p.goles_l !== null && p.goles_v !== null && stats[p.local] && stats[p.visitante]) {
            const sL = stats[p.local], sV = stats[p.visitante];
            const gl = parseInt(p.goles_l), gv = parseInt(p.goles_v);
            
            sL.PJ++; sV.PJ++; sL.GF += gl; sL.GC += gv; sV.GF += gv; sV.GC += gl;
            sL.DG = sL.GF - sL.GC; sV.DG = sV.GF - sV.GC;
            
            if (gl > gv) { sL.G++; sL.PTS += 3; sV.P++; }
            else if (gv > gl) { sV.G++; sV.PTS += 3; sL.P++; }
            else { sL.E++; sV.E++; sL.PTS += 1; sV.PTS += 1; }
        }
    });

    let html = `<h2>📊 Tabla de Posiciones</h2>`;
    const grupos = [...new Set(Object.values(stats).map(s => s.grupo))].sort();

    grupos.forEach(g => {
        html += `<div class="card" style="margin-bottom:15px;">
                    <div class="header-grid grid-posiciones">
                        <span>GRUPO ${g}</span><span>PJ</span><span>G</span><span>E</span><span>P</span><span>DG</span><span>PTS</span>
                    </div>`;
        const ranking = Object.values(stats).filter(s => s.grupo === g).sort((a,b) => b.PTS - a.PTS || b.DG - a.DG);
        ranking.forEach(eq => {
            // El logo ahora puede ser una URL de archivo o Base64
            const logoSrc = eq.logo ? (eq.logo.startsWith('http') || eq.logo.startsWith('/') ? eq.logo : `data:image/png;base64,${eq.logo}`) : '';
            
            html += `<div class="grid-posiciones">
                        <div class="team-cell"><img src="${logoSrc}" class="mini-logo">${eq.nombre}</div>
                        <span>${eq.PJ}</span><span>${eq.G}</span><span>${eq.E}</span><span>${eq.P}</span><span>${eq.DG}</span><span class="txt-gold">${eq.PTS}</span>
                    </div>`;
        });
        html += `</div>`;
    });
    container.innerHTML = html;
}

function renderizarResultadosYProximos() {
    const resContainer = document.getElementById("resultados");
    const proxContainer = document.getElementById("proximos");
    if (!resContainer || !proxContainer) return;
    
    const fechasUnicas = [...new Set(torneoData.partidos.map(p => p.fecha))].sort().reverse();
    
    let resHtml = `<h2>⚽ Últimos Resultados</h2>`;
    let proxHtml = `<h2>🗓️ Próximos Partidos</h2>`;

    fechasUnicas.forEach(fecha => {
        const partidosDeFecha = torneoData.partidos.filter(p => p.fecha === fecha);
        const terminados = partidosDeFecha.filter(p => p.goles_l !== null);
        const pendientes = partidosDeFecha.filter(p => p.goles_l === null);

        if (terminados.length > 0) {
            resHtml += `<div class="date-divider">${formatearFechaEspanol(fecha)}</div>`;
            resHtml += `<div class="card" style="margin-bottom:20px; border-radius: 0 8px 8px 8px;">`;
            terminados.forEach(p => resHtml += generarFilaPartido(p));
            resHtml += `</div>`;
        }

        if (pendientes.length > 0) {
            proxHtml += `<div class="date-divider">${formatearFechaEspanol(fecha)}</div>`;
            proxHtml += `<div class="card" style="margin-bottom:20px; border-radius: 0 8px 8px 8px;">`;
            pendientes.forEach(p => proxHtml += generarFilaPartido(p));
            proxHtml += `</div>`;
        }
    });

    resContainer.innerHTML = resHtml;
    proxContainer.innerHTML = proxHtml;
}

function generarFilaPartido(p) {
    const eqL = Object.values(torneoData.equipos).find(e => e.nombre === p.local);
    const eqV = Object.values(torneoData.equipos).find(e => e.nombre === p.visitante);
    
    const getLogo = (eq) => eq?.logo ? (eq.logo.startsWith('http') || eq.logo.startsWith('/') ? eq.logo : `data:image/png;base64,${eq.logo}`) : '';

    return `
        <div class="match-item">
            <div class="team-cell" style="justify-content:flex-end;">${p.local} <img src="${getLogo(eqL)}" class="mini-logo"></div>
            <div class="score-box">${p.goles_l !== null ? p.goles_l + " - " + p.goles_v : "VS"}</div>
            <div class="team-cell"><img src="${getLogo(eqV)}" class="mini-logo"> ${p.visitante}</div>
        </div>`;
}

function renderizarGoleadores() {
    const container = document.getElementById("goleadores");
    if (!container) return;
    let html = `<h2>👟 Tabla de Goleadores</h2><div class="card">
                <div class="header-grid grid-goleadores"><span></span><span>EQUIPO</span><span>JUGADOR</span><span style="text-align:center;">GOLES</span></div>`;
    
    const lista = [...torneoData.goleadores].sort((a,b) => b.goles - a.goles);
    lista.forEach((g, i) => {
        const eq = Object.values(torneoData.equipos).find(e => e.nombre === g.equipo);
        const logo = eq?.logo ? (eq.logo.startsWith('http') || eq.logo.startsWith('/') ? eq.logo : `data:image/png;base64,${eq.logo}`) : '';
        const esTop = i === 0 ? "top-scorer-card" : "";
        
        html += `<div class="grid-goleadores ${esTop}">
                    <img src="${logo}" class="mini-logo">
                    <span class="team-name-wrap">${g.equipo}</span>
                    <span class="${i===0?'top-scorer-name':''}">${g.nombre}</span>
                    <span class="txt-gold" style="text-align:center;font-weight:900;">${g.goles}</span>
                </div>`;
    });
    container.innerHTML = html + `</div>`;
}

function renderizarFaseFinal() {
    const container = document.getElementById("fase-final");
    if (!container || !torneoData.fase_final) return;

    let html = `<h2>🏆 Cuadro de Fase Final</h2><div class="bracket-container">`;
    const rondasKeys = Object.keys(torneoData.fase_final);

    rondasKeys.forEach(rondaKey => {
        let partidosRonda = torneoData.fase_final[rondaKey];
        if (!Array.isArray(partidosRonda)) {
            partidosRonda = [partidosRonda];
        }

        html += `<div class="bracket-round"><h3>${rondaKey.toUpperCase().replace("_", " ")}</h3>`;
        partidosRonda.forEach(p => {
            if (!p) return;
            const winL = p.goles_l !== null && p.goles_l > p.goles_v;
            const winV = p.goles_v !== null && p.goles_v > p.goles_l;

            const eqL = Object.values(torneoData.equipos).find(e => e.nombre === p.local);
            const eqV = Object.values(torneoData.equipos).find(e => e.nombre === p.visitante);
            
            const getLogoTag = (eq) => {
                if (!eq?.logo) return '';
                const src = (eq.logo.startsWith('http') || eq.logo.startsWith('/')) ? eq.logo : `data:image/png;base64,${eq.logo}`;
                return `<img src="${src}" class="mini-logo">`;
            };

            html += `
                <div class="match-bracket">
                    <div class="team-bracket ${winL ? 'winner' : ''}">
                        <span>${getLogoTag(eqL)} ${p.local || 'TBD'}</span>
                        <span class="score-bracket">${p.goles_l ?? '-'}</span>
                    </div>
                    <div class="team-bracket ${winV ? 'winner' : ''}">
                        <span>${getLogoTag(eqV)} ${p.visitante || 'TBD'}</span>
                        <span class="score-bracket">${p.goles_v ?? '-'}</span>
                    </div>
                </div>`;
        });
        html += `</div>`;
    });

    html += `</div>`;
    container.innerHTML = html;
}

// ==========================================
// 4. LÓGICA DE ADMINISTRACIÓN
// ==========================================

function verificarPassword() {
    const pass = document.getElementById("admin-password").value;
    if (pass === "organizadores2026") {
        document.getElementById("admin-login").style.display = "none";
        document.getElementById("admin-panel").style.display = "block";
    } else { alert("Clave incorrecta"); }
}

function cerrarSesion() {
    document.getElementById("admin-login").style.display = "block";
    document.getElementById("admin-panel").style.display = "none";
    document.getElementById("admin-password").value = "";
}

function llenarSelectsEquipos() {
    const selects = ["new-player-team", "match-team-l", "match-team-v"];
    const nombres = Object.values(torneoData.equipos).map(e => e.nombre).sort();
    selects.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = nombres.map(n => `<option value="${n}">${n}</option>`).join("");
    });
}

// --- GESTIÓN DE EQUIPOS (NUEVO) ---

async function subirLogoAlServidor(file) {
    if (!file) return null;
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/upload_logo', {
            method: 'POST',
            body: formData
        });
        if (!response.ok) throw new Error("Error al subir imagen");
        const data = await response.json();
        return data.logo_url;
    } catch (e) {
        console.error(e);
        return null;
    }
}

async function agregarEquipo() {
    const nombre = document.getElementById("new-team-name").value.trim();
    const grupo = document.getElementById("new-team-group").value;
    const logoFile = document.getElementById("new-team-logo").files[0];

    if (!nombre) { alert("El nombre es obligatorio"); return; }
    
    const logoUrl = await subirLogoAlServidor(logoFile);
    const id = nombre.toLowerCase().replace(/\s+/g, '_');

    torneoData.equipos[id] = {
        nombre: nombre,
        grupo: grupo,
        logo: logoUrl || "",
        pj: 0, pg: 0, pe: 0, pp: 0, gf: 0, gc: 0, pts: 0
    };

    alert("Equipo creado localmente. ¡Recuerda Guardar Todo!");
    document.getElementById("new-team-name").value = "";
    document.getElementById("new-team-logo").value = "";
    document.getElementById("file-name-display").innerText = "Sin archivo";
    actualizarInterfaz();
}

function renderizarAdminEquipos() {
    const list = document.getElementById("admin-teams-list");
    if (!list) return;

    list.innerHTML = Object.keys(torneoData.equipos).map(id => {
        const eq = torneoData.equipos[id];
        const logoSrc = eq.logo ? (eq.logo.startsWith('http') || eq.logo.startsWith('/') ? eq.logo : `data:image/png;base64,${eq.logo}`) : '';
        
        return `
        <div class="admin-item" style="display:grid; grid-template-columns: 50px 1fr auto; gap:10px; align-items:center; background:rgba(255,255,255,0.05); padding:10px; margin-bottom:10px; border-radius:8px;">
            <img src="${logoSrc}" style="width:40px; height:40px; border-radius:5px; object-fit:contain;">
            <div>
                <input type="text" value="${eq.nombre}" onchange="editarNombreEquipo('${id}', this.value)" style="width:100%; margin-bottom:5px;">
                <select onchange="editarGrupoEquipo('${id}', this.value)" style="width:100px; font-size:0.7rem;">
                    <option value="A" ${eq.grupo==='A'?'selected':''}>Grupo A</option>
                    <option value="B" ${eq.grupo==='B'?'selected':''}>Grupo B</option>
                    <option value="C" ${eq.grupo==='C'?'selected':''}>Grupo C</option>
                    <option value="D" ${eq.grupo==='D'?'selected':''}>Grupo D</option>
                    <option value="SIN GRUPO" ${eq.grupo==='SIN GRUPO'?'selected':''}>Sin Grupo</option>
                </select>
            </div>
            <div style="text-align:right;">
                <input type="file" id="update-logo-${id}" accept="image/*" style="display:none;" onchange="actualizarLogoEquipo('${id}', this.files[0])">
                <button class="btn-small" onclick="document.getElementById('update-logo-${id}').click()">🖼️ Logo</button>
                <button class="btn-small" style="background:#cc0000;" onclick="eliminarEquipo('${id}')">🗑️</button>
            </div>
        </div>`;
    }).join("");
}

function editarNombreEquipo(id, nuevoNombre) {
    torneoData.equipos[id].nombre = nuevoNombre;
    actualizarInterfaz();
}

function editarGrupoEquipo(id, nuevoGrupo) {
    torneoData.equipos[id].grupo = nuevoGrupo;
    actualizarInterfaz();
}

async function actualizarLogoEquipo(id, file) {
    const url = await subirLogoAlServidor(file);
    if (url) {
        torneoData.equipos[id].logo = url;
        actualizarInterfaz();
    }
}

function eliminarEquipo(id) {
    if (confirm(`¿Eliminar al equipo ${torneoData.equipos[id].nombre}? Se borrará de tablas y partidos.`)) {
        delete torneoData.equipos[id];
        actualizarInterfaz();
    }
}

// --- RESTO DE GESTIÓN (PARTIDOS, GOLEADORES, FASE FINAL) ---

function renderizarAdminPartidos() {
    const list = document.getElementById("admin-partidos-list");
    if (!list) return;
    list.innerHTML = torneoData.partidos.map((p, i) => `
        <div class="admin-item" style="display:flex; justify-content:space-between; align-items:center; padding:10px; background:rgba(255,255,255,0.05); margin-bottom:5px; border-radius:5px;">
            <div style="font-size:0.8rem;">${p.fecha}<br><strong>${p.local} vs ${p.visitante}</strong></div>
            <div>
                <input type="number" id="gl-${i}" value="${p.goles_l !== null ? p.goles_l : ''}" style="width:40px; background:#000; color:white; border:1px solid #7db1ff;">
                <input type="number" id="gv-${i}" value="${p.goles_v !== null ? p.goles_v : ''}" style="width:40px; background:#000; color:white; border:1px solid #7db1ff;">
                <button class="btn-add" style="background:#28a745; padding:5px;" onclick="guardarResultado(${i})">✔️</button>
                <button class="btn-small" onclick="eliminarPartido(${i})">🗑️</button>
            </div>
        </div>`).reverse().join("");
}

function agendarPartido() {
    const f = document.getElementById("match-date").value;
    const l = document.getElementById("match-team-l").value;
    const v = document.getElementById("match-team-v").value;
    if (f && l !== v) {
        torneoData.partidos.push({ fecha: f, local: l, visitante: v, goles_l: null, goles_v: null });
        actualizarInterfaz();
    }
}

function guardarResultado(i) {
    const l = document.getElementById(`gl-${i}`).value;
    const v = document.getElementById(`gv-${i}`).value;
    torneoData.partidos[i].goles_l = l === "" ? null : parseInt(l);
    torneoData.partidos[i].goles_v = v === "" ? null : parseInt(v);
    actualizarInterfaz();
}

function eliminarPartido(i) {
    if (confirm("¿Eliminar este partido?")) { torneoData.partidos.splice(i, 1); actualizarInterfaz(); }
}

function renderizarAdminGoleadores() {
    const list = document.getElementById("admin-goleadores-list");
    if (!list) return;
    list.innerHTML = torneoData.goleadores.map((g, i) => `
        <div class="admin-item" style="display:flex; justify-content:space-between; align-items:center; padding:10px; background:rgba(255,255,255,0.05); margin-bottom:5px; border-radius:5px;">
            <span>${g.nombre} <small style="color:#7db1ff;">(${g.equipo})</small></span>
            <div>
                <button class="btn-small" onclick="cambiarGoles(${i}, -1)">-</button>
                <span style="margin:0 10px; font-weight:900;">${g.goles}</span>
                <button class="btn-small" onclick="cambiarGoles(${i}, 1)">+</button>
                <button class="btn-small" style="margin-left:10px; background:#666;" onclick="eliminarGoleador(${i})">🗑️</button>
            </div>
        </div>`).join("");
}

function cambiarGoles(i, c) {
    torneoData.goleadores[i].goles = Math.max(0, torneoData.goleadores[i].goles + c);
    actualizarInterfaz();
}

function agregarJugador() {
    const n = document.getElementById("new-player-name").value.toUpperCase();
    const e = document.getElementById("new-player-team").value;
    const g = parseInt(document.getElementById("new-player-goals").value) || 0;
    if (n) {
        torneoData.goleadores.push({ nombre: n, equipo: e, goles: g });
        document.getElementById("new-player-name").value = "";
        actualizarInterfaz();
    }
}

function eliminarGoleador(i) {
    if (confirm("¿Eliminar goleador?")) { torneoData.goleadores.splice(i, 1); actualizarInterfaz(); }
}

function renderizarAdminFaseFinal() {
    const container = document.getElementById("admin-fase-final-list");
    if (!container || !torneoData.fase_final) return;

    const nombresEquipos = Object.values(torneoData.equipos).map(e => e.nombre).sort();
    const opcionesEquipos = `<option value="">TBD (Por definir)</option>` + 
                            nombresEquipos.map(n => `<option value="${n}">${n}</option>`).join("");

    let html = "";
    const rondas = Object.keys(torneoData.fase_final);

    rondas.forEach(rondaKey => {
        let partidos = torneoData.fase_final[rondaKey];
        if (!Array.isArray(partidos)) partidos = [partidos]; 

        html += `<div style="margin-bottom: 15px; border-bottom: 1px solid rgba(255,215,0,0.1); padding-bottom: 10px;">
                    <h4 style="color: #FFD700; text-transform: uppercase; margin-bottom: 10px; font-size:0.8rem;">${rondaKey.replace("_", " ")}</h4>`;

        partidos.forEach((p, i) => {
            if (!p) return;
            const selL = opcionesEquipos.replace(`value="${p.local}"`, `value="${p.local}" selected`);
            const selV = opcionesEquipos.replace(`value="${p.visitante}"`, `value="${p.visitante}" selected`);

            html += `
                <div class="admin-item" style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center; background: rgba(0,0,0,0.2); padding: 8px; border-radius: 5px; margin-bottom: 5px;">
                    <select id="ff-l-${rondaKey}-${i}" style="flex: 1; min-width: 90px; font-size:0.8rem;">${selL}</select>
                    <input type="number" id="ff-gl-${rondaKey}-${i}" value="${p.goles_l ?? ''}" style="width: 40px; font-size:0.8rem;" placeholder="0">
                    <span class="txt-gold" style="font-size:0.7rem;">VS</span>
                    <input type="number" id="ff-gv-${rondaKey}-${i}" value="${p.goles_v ?? ''}" style="width: 40px; font-size:0.8rem;" placeholder="0">
                    <select id="ff-v-${rondaKey}-${i}" style="flex: 1; min-width: 90px; font-size:0.8rem;">${selV}</select>
                    <button class="btn-add" style="background: #28a745; padding: 5px 8px;" onclick="guardarResultadoFaseFinal('${rondaKey}', ${i})">✔️</button>
                </div>`;
        });
        html += `</div>`;
    });

    container.innerHTML = html;
}

function guardarResultadoFaseFinal(ronda, index) {
    const local = document.getElementById(`ff-l-${ronda}-${index}`).value;
    const visitante = document.getElementById(`ff-v-${ronda}-${index}`).value;
    const gl = document.getElementById(`ff-gl-${ronda}-${index}`).value;
    const gv = document.getElementById(`ff-gv-${ronda}-${index}`).value;

    let target;
    if (Array.isArray(torneoData.fase_final[ronda])) {
        target = torneoData.fase_final[ronda][index];
    } else {
        target = torneoData.fase_final[ronda];
    }

    target.local = local || null;
    target.visitante = visitante || null;
    target.goles_l = gl === "" ? null : parseInt(gl);
    target.goles_v = gv === "" ? null : parseInt(gv);

    actualizarInterfaz();
}

// ==========================================
// 5. COMUNICACIÓN CON EL SERVIDOR
// ==========================================
async function guardarCambiosServidor() {
    try {
        const response = await fetch('/guardar', { // URL RELATIVA
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(torneoData)
        });
        if (response.ok) {
            alert("✅ ¡Éxito! Los cambios y logos se guardaron permanentemente.");
        } else {
            alert("❌ Error: El servidor rechazó la petición.");
        }
    } catch (e) {
        alert("❌ Error: No se pudo conectar con el servidor.");
    }
}
