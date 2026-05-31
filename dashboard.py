HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>QEEG Clinical Report</title>
    <style>
        body { background:#0a0a0a; color:#d0d0d0; font-family: sans-serif; margin:0; padding:10px; }
        .header { background:#161616; padding:15px; border-radius:8px; border-bottom:3px solid #3498db; display:flex; gap:10px; align-items: center; }
        .window { background:#161616; border-radius:8px; margin-top:10px; border:1px solid #333; overflow:hidden; }
        .title { background:#222; padding:8px; font-size:11px; color:#3498db; font-weight:bold; text-transform:uppercase; }
        canvas { background:#0d0d0d; display:block; margin:0 auto; }
        .matrix-table { border-collapse:collapse; width:100%; font-size:11px; text-align:center; }
        .matrix-table th, .matrix-table td { border:1px solid #222; padding:8px; }
        .btn-test { background: #27ae60; color: white; border: none; padding: 10px 20px; font-weight: bold; border-radius: 4px; cursor: pointer; text-transform: uppercase; font-size: 11px; }
        .btn-test.activo { background: #e74c3c; }
    </style>
</head>
<body>
    <div class="header">
        <input type="text" id="paciente" placeholder="PACIENTE..." style="background:#222; border:1px solid #444; color:#0ff; padding:10px; border-radius:4px;">
        <button id="btnIniciar" class="btn-test" onclick="toggleTest()">Iniciar Test</button>
        <div id="statusLabel" style="margin-left:auto; color:#95a5a6; font-weight:bold;">SISTEMA EN ESPERA</div>
    </div>

    <div class="window">
        <div class="title">Espectro de Potencia Fp1 (uV)</div>
        <canvas id="cvBars" width="940" height="150"></canvas>
    </div>

    <div class="window" id="matrizContainer"></div>

    <div class="window">
        <div class="title">Trazado EEG Frontal</div>
        <canvas id="cvWaves" width="900" height="300"></canvas>
    </div>

<script>
const bandas = ["Delta", "Theta", "LowAlpha", "HighAlpha", "Alpha", "LowBeta", "HighBeta", "Beta", "Gamma"];
let testInterval = null;

function prepararTabla() {
    let h = "<table class='matrix-table'><tr><th>#</th><th>ZONA</th>";
    bandas.forEach(b => h += "<th>"+b+"</th>");
    h += "</tr><tr><td>1</td><td>Fp1</td>";
    bandas.forEach(b => h += "<td id='v-0-"+b+"'>-</td>");
    document.getElementById("matrizContainer").innerHTML = h + "</tr></table>";
}

function toggleTest() {
    const btn = document.getElementById("btnIniciar");
    const status = document.getElementById("statusLabel");

    if (!testInterval) {
        testInterval = setInterval(() => {
            fetch("/data")
                .then(r => r.json())
                .then(update)
                .catch(e => console.log("Esperando datos..."));
        }, 500);

        btn.innerText = "Detener Test";
        btn.classList.add("activo");
        status.innerText = "COLECTANDO DATOS";
        status.style.color = "#f1c40f";
    } else {
        clearInterval(testInterval);
        testInterval = null;

        btn.innerText = "Iniciar Test";
        btn.classList.remove("activo");
        status.innerText = "TEST DETENIDO";
        status.style.color = "#e74c3c";
    }
}

function update(d) {
    const ctxB = document.getElementById("cvBars").getContext("2d");
    const ctxW = document.getElementById("cvWaves").getContext("2d");

    ctxB.clearRect(0,0,940,150);

    bandas.forEach((b, i) => {
        let val = d.fp1[b] || 0;
        ctxB.fillStyle = "#3498db";
        ctxB.fillRect(60 + i * 95, 130 - (val*2.5), 45, val*2.5);
        document.getElementById("v-0-"+b).innerText = val.toFixed(1);
    });

    ctxW.clearRect(0,0,900,300);
    ctxW.strokeStyle = "#00ff00";
    ctxW.lineWidth = 2;
    ctxW.beginPath();

    d.raw["Fp1"].forEach((p, x) => {
        if(x == 0) {
            ctxW.moveTo(x*25, 150-p);
        } else {
            ctxW.lineTo(x*25, 150-p);
        }
    });

    ctxW.stroke();
}

window.onload = prepararTabla;
</script>
</body>
</html>"""
