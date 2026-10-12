document.addEventListener("DOMContentLoaded",() =>{
  const wsProto =window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl=`${wsProto}//${window.location.host}/ws`;

  let socket = null;
  const canvas = document.getElementById("arm-canvas");
  const ctx =canvas.getContext("2d");

  const valBase= document.getElementById("val-base");
  const valShoulder = document.getElementById("val-shoulder");
  const valElbow=document.getElementById("val-elbow");


  const valWPitch =document.getElementById("val-wpitch");
  const valWRoll = document.getElementById("val-wroll");
  const valGripper = document.getElementById("val-gripper");

  const barBase =document.getElementById("bar-base");

  const barShoulder = document.getElementById("bar-shoulder");
  const barElbow = document.getElementById("bar-elbow");
  const barWPitch = document.getElementById("bar-wpitch");
  const barWRoll = document.getElementById("bar-wroll");
  const barGripper=document.getElementById("bar-gripper");



  const fkBadge = document.getElementById("fk-badge");
  const execState = document.getElementById("exec-state");
  const logsList=document.getElementById("logs-list");
  const cmdForm = document.getElementById("cmd-form");
  const cmdInput= document.getElementById("cmd-input");
  const btnEstop=document.getElementById("btn-estop");


  const btnReset = document.getElementById("btn-reset");

  let latestJoints3D = [];

  function connectWebSocket() {
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      appendLog("SYSTEM", "Connected to Robot Arm Telemetry stream.");
    };

    socket.onmessage = (event) => {

      try {
        const data=JSON.parse(event.data);
        if (data.type === "telemetry") {
          updateGauges(data.angles);
          latestJoints3D =data.joints_3d;
          renderArm(data.joints_3d);
        } else if (data.type === "log") {
          appendLog(data.stage, data.message);
          execState.innerText= data.stage;
          if(data.stage === "COMPLETED"){
            execState.className = "badge badge-accent";
          } else if (data.stage === "FAILED") {
            execState.className ="badge btn-danger";
          }
        }
      } catch (err) {
        console.error("Error parsing WS packet:", err);
      }
    };

    socket.onclose = ()=>{


      appendLog("SYSTEM","Disconnected from Telemetry stream. Reconnecting in 3s...");
      setTimeout(connectWebSocket, 3000);
    };
  }

  function updateGauges(angles) {
    if (!angles)return;
    valBase.innerText=`${angles.base_yaw.toFixed(1)}°`;
    valShoulder.innerText = `${angles.shoulder_pitch.toFixed(1)}°`;
    valElbow.innerText =`${angles.elbow_pitch.toFixed(1)}°`;
    valWPitch.innerText = `${angles.wrist_pitch.toFixed(1)}°`;
    valWRoll.innerText = `${angles.wrist_roll.toFixed(1)}°`;
    valGripper.innerText=`${angles.gripper.toFixed(1)}°`;

    barBase.style.width = `${(angles.base_yaw / 180) * 100}%`;
    barShoulder.style.width =`${(angles.shoulder_pitch / 180) * 100}%`;


    barElbow.style.width = `${(angles.elbow_pitch / 180) * 100}%`;
    barWPitch.style.width =`${(angles.wrist_pitch / 180) * 100}%`;
    barWRoll.style.width = `${(angles.wrist_roll / 180) * 100}%`;
    barGripper.style.width = `${(angles.gripper / 180) * 100}%`;
  }

  // isometric projection matrix for 2d canvas rendering
  function project(x,y,z) {
    const cx = canvas.width / 2;
    const cy =canvas.height - 40;
    const scale =0.65;
    const rad=0.55;
    const px= cx + (x * Math.cos(rad) - y * 0.5)* scale;
    const py=cy -(z * 0.9 + y * 0.4)* scale;
    return{px,py };
  }

  function renderArm(joints) {
    ctx.clearRect(0,0,canvas.width, canvas.height);

    ctx.strokeStyle ="rgba(255, 255, 255, 0.05)";
    ctx.lineWidth= 1;
    for (let r = 50; r <= 220; r += 50) {

      ctx.beginPath();
      for (let a = -Math.PI / 2; a <= Math.PI / 2; a += 0.1) {
        const gx = r * Math.sin(a);
        const gy = r * Math.cos(a);
        const pt = project(gx, gy, 0);
        if (a === -Math.PI / 2) ctx.moveTo(pt.px, pt.py);
        else ctx.lineTo(pt.px, pt.py);
      }

      ctx.stroke();
    }

    if(!joints || joints.length === 0) return;

    // render manipulator links
    ctx.beginPath();
    const pts = joints.map(j => project(j.x, j.y, j.z));
    ctx.moveTo(pts[0].px,pts[0].py);
    for (let i = 1; i < pts.length; i++) {
      ctx.lineTo(pts[i].px, pts[i].py);
    }
    ctx.strokeStyle = "#00f2fe";
    ctx.lineWidth =6;


    ctx.lineCap = "round";
    ctx.lineJoin= "round";
    ctx.stroke();

    //render joints circles
    pts.forEach((pt,idx)=>{
      ctx.beginPath();
      const r= idx === 0 ? 8 : (idx === pts.length - 1 ? 5 : 6);
      ctx.arc(pt.px, pt.py, r, 0, Math.PI * 2);
      ctx.fillStyle = idx === pts.length - 1 ? "#ef4444" : (idx === 0 ? "#6b7280" : "#ffffff");
      ctx.fill();
      ctx.strokeStyle = "#0f172a";


      ctx.lineWidth =2;

      ctx.stroke();
    });

    const tcp = joints[joints.length - 1];
    if (tcp) {
      fkBadge.innerText=`TCP: (${tcp.x.toFixed(1)}, ${tcp.y.toFixed(1)}, ${tcp.z.toFixed(1)}) mm`;


    }
  }

  function appendLog(stage, message) {
    const entry = document.createElement("div");
    entry.className = "log-entry";
    const now=new Date().toTimeString().split(" ")[0];
    entry.innerHTML= `<span class="log-time">${now}</span> <span class="log-stage-${stage}">[${stage}]</span> ${message}`;
    logsList.appendChild(entry);

    logsList.scrollTop = logsList.scrollHeight;
  }

  cmdForm.addEventListener("submit", async (e) =>{
    e.preventDefault();
    const text = cmdInput.value.trim();
    if (!text)return;
    cmdInput.value= "";
    execState.innerText="STARTING";

    try {


      const resp = await fetch("/api/command",{
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instruction: text})
      });
      const data =await resp.json();
      appendLog("INPUT",`Command sent: "${text}"`);
    } catch(err){
      appendLog("FAILED", `Error sending command: ${err}`);
    }
  });

  document.querySelectorAll(".chip").forEach(btn => {
    btn.addEventListener("click", () => {
      cmdInput.value=btn.dataset.cmd;
      cmdForm.dispatchEvent(new Event("submit"));
    });
  });

  btnEstop.addEventListener("click", async () => {
    await fetch("/api/estop", { method: "POST" });
    appendLog("ALERT", "EMERGENCY STOP TRIGGERED!");

    execState.innerText = "ESTOP";
    execState.className= "badge btn-danger";
  });

  btnReset.addEventListener("click",async () =>{
    await fetch("/api/reset_estop", { method: "POST"});
    cmdInput.value = "home";
    cmdForm.dispatchEvent(new Event("submit"));
  });

  connectWebSocket();
});

