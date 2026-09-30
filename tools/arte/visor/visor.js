// Visor de arte: lê assets/previews/visor.json a cada 2 s e mostra a prévia mais nova (imagem, GIF ou GLB).
// Os caminhos do visor.json são relativos à raiz da worktree; o servir.py só entrega assets/ e tools/arte/visor/.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const VISOR_JSON = '/assets/previews/visor.json';
const $ = (id) => document.getElementById(id);
const url = (caminho) => '/' + caminho.replace(/^\/+/, '');
const guardar = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* sem armazenamento */ } };
const lembrar = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };

const config = await (await fetch('personagens.json', { cache: 'no-store' })).json();

// ---------- lista e sondagem ----------

let itens = [];
let textoVisor = '';
let atual = null;         // chave do item mostrado
let chaveMaisNovo = null;

const chave = (it) => `${it.quando}|${it.caminho}`;

async function sondar() {
  try {
    const r = await fetch(VISOR_JSON, { cache: 'no-store' });
    if (!r.ok) throw new Error(r.status);
    const texto = await r.text();
    $('estado').textContent = '';
    if (texto === textoVisor) return;
    textoVisor = texto;
    const dados = JSON.parse(texto);
    itens = (Array.isArray(dados) ? dados : dados.itens || []).slice();
    itens.sort((a, b) => String(b.quando).localeCompare(String(a.quando)));
    const novo = itens.length ? chave(itens[0]) : null;
    desenharLista();
    // Chegou prévia nova: vai para ela. Senão, fica onde o Arthur está.
    if (novo !== chaveMaisNovo) {
      chaveMaisNovo = novo;
      if (itens.length) mostrar(itens[0]);
    }
  } catch (e) {
    $('estado').textContent = '· sem visor.json';
  }
}

function desenharLista() {
  const ol = $('lista');
  ol.innerHTML = '';
  itens.forEach((it, i) => {
    const li = document.createElement('li');
    if (i === 0) li.classList.add('novo');
    if (chave(it) === atual) li.classList.add('atual');
    const t = document.createElement('span'); t.className = 't'; t.textContent = it.titulo || it.caminho;
    const q = document.createElement('span'); q.className = 'q'; q.textContent = `${it.quando} · ${it.tipo}`;
    li.append(t, q);
    li.onclick = () => mostrar(it);
    ol.append(li);
  });
}

function mostrar(it) {
  atual = chave(it);
  desenharLista();
  $('titulo').textContent = it.titulo || it.caminho;
  const junto = (it.junto || []).map((j) => (typeof j === 'string' ? j : j.caminho));
  $('meta').textContent = `${it.quando} · ${it.tipo} · ${it.caminho}${it.altura ? ` (normalizado a ${it.altura} m)` : ''}` +
    `${junto.length ? ' + ' + junto.join(', ') : ''}`;
  $('nota').textContent = it.nota || '';
  $('vazio').hidden = true;
  if (it.tipo === 'glb') mostrar3d(it);
  else if (it.tipo === 'texto') mostrarTexto(it);
  else mostrarImagem(it);
}

// ---------- crepúsculo (tudo × #6A5B7C, imagem ou 3D) ----------

document.documentElement.style.setProperty('--crepusculo', config.cena.crepusculo);
document.documentElement.style.setProperty('--palco', config.cena.fundo);
let crepusculo = lembrar('visor.crepusculo') === '1';
function aplicarCrepusculo() {
  $('filtro-crepusculo').hidden = !crepusculo;
  $('crepusculo').classList.toggle('ativo', crepusculo);
}
$('crepusculo').onclick = () => { crepusculo = !crepusculo; guardar('visor.crepusculo', crepusculo ? '1' : '0'); aplicarCrepusculo(); };
aplicarCrepusculo();

// ---------- imagem e GIF: tamanho real (1 px da imagem = 1 px da tela), zoom e arrastar ----------

const img = $('imagem');
const caixaImg = $('vista-imagem');
let escala = 1; // 1 = tamanho real

// ---------- texto (Markdown simples: títulos, listas, tabelas, negrito, código) ----------

function escapar(t) {
  return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function inline(t) {
  return escapar(t).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
}

function markdown(md) {
  const out = [];
  const linhas = md.split('\n');
  for (let i = 0; i < linhas.length; i++) {
    const l = linhas[i];
    if (/^\s*\|/.test(l)) { // tabela: cabeçalho, separador, linhas
      const bloco = [];
      while (i < linhas.length && /^\s*\|/.test(linhas[i])) bloco.push(linhas[i++]);
      i--;
      const cel = (r) => r.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
      const alin = cel(bloco[1] || '').map((c) => /-:$/.test(c) ? ' class="num"' : '');
      const cab = cel(bloco[0]).map((c, k) => `<th${alin[k] || ''}>${inline(c)}</th>`).join('');
      const corpo = bloco.slice(2).map((r) => '<tr>' + cel(r).map((c, k) => `<td${alin[k] || ''}>${inline(c)}</td>`).join('') + '</tr>').join('');
      out.push(`<table><thead><tr>${cab}</tr></thead><tbody>${corpo}</tbody></table>`);
    } else if (/^\s*[-*] /.test(l)) {
      const itens = [];
      while (i < linhas.length && /^\s*[-*] /.test(linhas[i])) itens.push(linhas[i++].replace(/^\s*[-*] /, ''));
      i--;
      out.push('<ul>' + itens.map((x) => `<li>${inline(x)}</li>`).join('') + '</ul>');
    } else if (/^#{1,3} /.test(l)) {
      const n = l.match(/^#+/)[0].length;
      out.push(`<h${n}>${inline(l.slice(n + 1))}</h${n}>`);
    } else if (l.trim()) {
      out.push(`<p>${inline(l)}</p>`);
    }
  }
  return out.join('\n');
}

async function mostrarTexto(it) {
  pararCena();
  $('vista-3d').hidden = true; $('barra-3d').hidden = true; $('clipes').hidden = true;
  caixaImg.hidden = true; $('barra-imagem').hidden = true;
  $('vista-texto').hidden = false;
  const r = await fetch(url(it.caminho), { cache: 'no-store' });
  $('texto').innerHTML = r.ok ? markdown(await r.text()) : `<p>não carregou (${r.status})</p>`;
}

function mostrarImagem(it) {
  pararCena();
  $('vista-texto').hidden = true;
  $('vista-3d').hidden = true; $('barra-3d').hidden = true; $('clipes').hidden = true;
  caixaImg.hidden = false; $('barra-imagem').hidden = false;
  escala = 1;
  img.onload = () => aplicarEscala();
  img.src = url(it.caminho) + '?q=' + encodeURIComponent(it.quando);
}

function aplicarEscala(foco) {
  if (!img.naturalWidth) return;
  const dpr = window.devicePixelRatio || 1;
  const antes = { w: img.clientWidth || 1, sx: caixaImg.scrollLeft, sy: caixaImg.scrollTop };
  img.style.width = (img.naturalWidth / dpr) * escala + 'px';
  img.classList.toggle('pixelado', escala > 1);
  $('zoom-imagem').textContent = `${Math.round(escala * 100)}% · ${img.naturalWidth}×${img.naturalHeight}`;
  if (foco) { // mantém o ponto sob o cursor
    const k = img.clientWidth / antes.w;
    caixaImg.scrollLeft = (antes.sx + foco.x) * k - foco.x;
    caixaImg.scrollTop = (antes.sy + foco.y) * k - foco.y;
  }
}

$('barra-imagem').addEventListener('click', (e) => {
  const z = e.target.dataset.zoom;
  if (!z) return;
  if (z === '+') escala *= 1.25;
  else if (z === '-') escala /= 1.25;
  else if (z === 'real') escala = 1;
  else if (z === 'ajustar') {
    const dpr = window.devicePixelRatio || 1;
    escala = Math.min(caixaImg.clientWidth / (img.naturalWidth / dpr), caixaImg.clientHeight / (img.naturalHeight / dpr));
  }
  aplicarEscala();
});
caixaImg.addEventListener('wheel', (e) => {
  e.preventDefault();
  const r = caixaImg.getBoundingClientRect();
  escala = Math.min(16, Math.max(0.05, escala * Math.exp(-e.deltaY * 0.0015)));
  aplicarEscala({ x: e.clientX - r.left, y: e.clientY - r.top });
}, { passive: false });
let arrasto = null;
caixaImg.addEventListener('pointerdown', (e) => {
  arrasto = { x: e.clientX, y: e.clientY, sx: caixaImg.scrollLeft, sy: caixaImg.scrollTop };
  caixaImg.classList.add('arrastando'); caixaImg.setPointerCapture(e.pointerId); e.preventDefault();
});
caixaImg.addEventListener('pointermove', (e) => {
  if (!arrasto) return;
  caixaImg.scrollLeft = arrasto.sx - (e.clientX - arrasto.x);
  caixaImg.scrollTop = arrasto.sy - (e.clientY - arrasto.y);
});
caixaImg.addEventListener('pointerup', () => { arrasto = null; caixaImg.classList.remove('arrastando'); });

// ---------- 3D ----------

const tela = $('tela');
const caixa3d = $('vista-3d');
const renderer = new THREE.WebGLRenderer({ canvas: tela, antialias: true });
const cena = new THREE.Scene();
cena.background = new THREE.Color(config.cena.fundo);
const camera = new THREE.PerspectiveCamera(30, 1, 0.01, 200);
const controles = new OrbitControls(camera, tela);
controles.enableDamping = true;
const relogio = new THREE.Clock();
const carregador = new GLTFLoader();

// Luz (uniforms compartilhados por todos os materiais toon).
const deg = THREE.MathUtils.degToRad;
const corLinear = (rgb, energia) => new THREE.Color().setRGB(rgb[0], rgb[1], rgb[2], THREE.SRGBColorSpace).multiplyScalar(energia);
const sol = config.cena.sol;
const LUZ = {
  solDir: { value: new THREE.Vector3(
    Math.sin(deg(sol.azimute_graus)) * Math.cos(deg(sol.elevacao_graus)),
    Math.sin(deg(sol.elevacao_graus)),
    Math.cos(deg(sol.azimute_graus)) * Math.cos(deg(sol.elevacao_graus))).normalize() },
  solCor: { value: corLinear(sol.cor, sol.energia) },
  ambCor: { value: corLinear(config.cena.ambiente.cor, config.cena.ambiente.energia) },
};

// Toon de 3 faixas, como src/View/Toon.gdshaderinc: meio-Lambert, faixas floor(ndl·3)/2, piso configurável.
// Retalhos do rosto como VillagerFace.gdshader: UV cru do retalho + célula (quadro) da grade do rosto.json.
const VERT = /* glsl */`
#include <common>
#include <skinning_pars_vertex>
varying vec3 vN;
varying vec2 vUv;
void main() {
  #include <skinbase_vertex>
  #include <beginnormal_vertex>
  #include <skinnormal_vertex>
  #include <begin_vertex>
  #include <skinning_vertex>
  vN = normalize(mat3(modelMatrix) * objectNormal);
  vUv = uv;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(transformed, 1.0);
}`;
const FRAG = /* glsl */`
uniform vec3 albedo;
uniform float alfa;
uniform sampler2D mapa;
uniform bool usaMapa;
uniform vec2 grade;
uniform float quadro;
uniform float piso;
uniform vec3 solDir;
uniform vec3 solCor;
uniform vec3 ambCor;
uniform vec3 emissivo;
varying vec3 vN;
varying vec2 vUv;
void main() {
  vec3 cor = albedo;
  float a = alfa;
  if (usaMapa) {
    vec2 celula = vec2(mod(quadro, grade.x), floor(quadro / grade.x));
    vec4 t = texture2D(mapa, (vUv + celula) / grade);
    cor *= t.rgb;
    a *= t.a;
  }
  vec3 n = normalize(vN);
  float ndl = clamp(dot(n, solDir) * 0.5 + 0.5, 0.0, 1.0);
  float faixa = floor(ndl * 3.0) / 2.0;
  faixa = mix(piso, 1.0, clamp(faixa, 0.0, 1.0));
  gl_FragColor = vec4(cor * (ambCor + solCor * faixa) + emissivo, a);
  #include <colorspace_fragment>
}`;

function personagemDe(caminho) {
  const c = caminho.toLowerCase();
  for (const [nome, p] of Object.entries(config.personagens)) {
    if (p.reconhece.some((r) => c.includes(r))) return { nome, ...p };
  }
  return null;
}

const gradesCache = {};
async function gradesDo(perso) {
  if (!perso || !perso.rosto) return {};
  if (!gradesCache[perso.rosto]) {
    gradesCache[perso.rosto] = fetch(url(perso.rosto), { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
  }
  return gradesCache[perso.rosto];
}

function materialToon(orig, perso, grades) {
  const nome = (orig.name || '').replace(/\.\d+$/, '').toLowerCase();
  // Material sem nome (GLB bruto da Meshy) fica com a pele do personagem.
  const hex = perso && (perso.cores[nome] || (!nome && perso.cores.pele));
  const rosto = nome.startsWith('rosto_') ? grades[nome.slice(6)] : null;
  let albedo = hex ? new THREE.Color(hex) : (orig.color ? orig.color.clone() : new THREE.Color(1, 1, 1));
  if (rosto) albedo = new THREE.Color(1, 1, 1);
  const emissivo = new THREE.Color(0, 0, 0);
  if (perso && perso.emissivos.includes(nome)) {
    if (orig.emissive && orig.emissive.getHex() !== 0) emissivo.copy(orig.emissive).multiplyScalar(orig.emissiveIntensity ?? 1);
    else emissivo.copy(albedo);
  }
  const mapa = orig.map || null;
  if (mapa) mapa.wrapS = mapa.wrapT = THREE.ClampToEdgeWrapping;
  const transparente = !!(rosto || orig.transparent);
  const m = new THREE.ShaderMaterial({
    name: orig.name,
    vertexShader: VERT,
    fragmentShader: FRAG,
    uniforms: {
      albedo: { value: albedo },
      alfa: { value: orig.opacity ?? 1 },
      mapa: { value: mapa },
      usaMapa: { value: !!mapa },
      grade: { value: new THREE.Vector2(rosto ? rosto.colunas : 1, rosto ? rosto.linhas : 1) },
      quadro: { value: 0 },
      piso: { value: perso ? perso.piso : 0.35 },
      emissivo: { value: emissivo },
      ...LUZ,
    },
    transparent: transparente,
    depthWrite: !transparente,
    side: THREE.FrontSide,
  });
  return m;
}

async function carregarGlb(caminho) {
  const gltf = await carregador.loadAsync(url(caminho));
  const perso = personagemDe(caminho);
  const grades = await gradesDo(perso);
  let temMalha = false, temPele = false;
  gltf.scene.traverse((o) => {
    if (!o.isMesh) return;
    temMalha = true;
    if (o.isSkinnedMesh) { temPele = true; o.frustumCulled = false; }
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    const novos = mats.map((m) => materialToon(m, perso, grades));
    o.material = Array.isArray(o.material) ? novos : novos[0];
    if (novos.some((m) => m.transparent)) o.renderOrder = 1;
  });
  return { caminho, perso, raiz: gltf.scene, clipes: gltf.animations, temMalha, temPele };
}

// Espaço do esqueleto (o nó Armature, pai do osso raiz): é nele que o Godot compensa GetBoneGlobalRest.
function armaturaDe(raiz) {
  let arm = null;
  raiz.traverse((o) => { if (!arm && o.isSkinnedMesh) arm = o.skeleton.bones.find((b) => !b.parent || !b.parent.isBone)?.parent; });
  return arm || raiz;
}

let modelos = [];      // { raiz, mixer, clipes, principal }
let geracao = 0;       // descarta carregamentos antigos se o Arthur trocar de item no meio
let rodando = false;
let pausado = false;
let clipeAtual = null;

function pararCena() {
  rodando = false;
  for (const m of modelos) { m.mixer?.stopAllAction(); cena.remove(m.raiz); }
  modelos = [];
}

async function mostrar3d(it) {
  caixaImg.hidden = true; $('barra-imagem').hidden = true; $('vista-texto').hidden = true;
  caixa3d.hidden = false; $('barra-3d').hidden = false;
  pararCena();
  const minha = ++geracao;
  $('info-3d').textContent = 'carregando…';
  const juntos = (it.junto || []).map((j) => (typeof j === 'string' ? { caminho: j } : j));
  let carregados;
  try {
    carregados = await Promise.all([carregarGlb(it.caminho), ...juntos.map((j) => carregarGlb(j.caminho))]);
  } catch (e) {
    $('info-3d').textContent = 'erro ao carregar: ' + e.message;
    return;
  }
  if (minha !== geracao) return;
  const [principal, ...outros] = carregados;
  cena.add(principal.raiz);
  principal.raiz.updateMatrixWorld(true);
  if (it.altura) {
    // Bruto fora de escala: normaliza a esta altura, pés no chão e centro na origem (como o render_meshy.py).
    const cx = new THREE.Box3().setFromObject(principal.raiz, true);
    const k = it.altura / (cx.max.y - cx.min.y);
    principal.raiz.scale.setScalar(k);
    principal.raiz.position.set(-(cx.min.x + cx.max.x) / 2 * k, -cx.min.y * k, -(cx.min.z + cx.max.z) / 2 * k);
    principal.raiz.updateMatrixWorld(true);
  }
  const caixaPrincipal = new THREE.Box3().setFromObject(principal.raiz, true);
  let proximoX = caixaPrincipal.max.x + config.cena.ao_lado_folga_m;
  const clipesExtras = [];
  modelos = [{ ...principal, principal: true }];

  outros.forEach((o, i) => {
    const pedido = juntos[i];
    const arquivo = o.caminho.split('/').pop().toLowerCase();
    if (!o.temMalha) { // GLB só de clipes (esqueleto + animação): toca no principal, pelos nomes dos ossos
      clipesExtras.push(...o.clipes);
      return;
    }
    const encaixes = (o.perso || principal.perso || { encaixes: {} }).encaixes;
    const osso = pedido.osso || Object.entries(encaixes).find(([k]) => arquivo.includes(k))?.[1];
    const noOsso = !o.temPele && !pedido.lado && osso ? principal.raiz.getObjectByName(osso) : null;
    if (noOsso) {
      // Peça rígida modelada no espaço do corpo em repouso: presa no osso, compensando o repouso.
      const arm = armaturaDe(principal.raiz);
      noOsso.updateWorldMatrix(true, false);
      const m = new THREE.Matrix4().copy(noOsso.matrixWorld).invert().multiply(arm.matrixWorld);
      m.decompose(o.raiz.position, o.raiz.quaternion, o.raiz.scale);
      noOsso.add(o.raiz);
    } else if (o.temPele || pedido.lado) {
      cena.add(o.raiz);
      o.raiz.updateMatrixWorld(true);
      const cx = new THREE.Box3().setFromObject(o.raiz, true);
      o.raiz.position.x += proximoX - cx.min.x;
      proximoX += cx.max.x - cx.min.x + config.cena.ao_lado_folga_m;
    } else {
      cena.add(o.raiz); // mesmo espaço, sem osso: fica onde está
    }
    modelos.push({ ...o, principal: false });
  });
  principal.clipes.push(...clipesExtras);
  for (const m of modelos) if (m.clipes.length && m.temPele) m.mixer = new THREE.AnimationMixer(m.raiz);

  desenharClipes();
  rodando = true;
  const inicial = nomesDeClipes().find((n) => n.includes('idle')) || null;
  if (inicial) tocar(inicial);
  vista(modoCamera.startsWith('jogo') ? modoCamera : 'tres_quartos');
}

// ---------- clipes ----------

function nomesDeClipes() {
  const nomes = [];
  for (const m of modelos) for (const c of m.clipes) if (m.mixer && !nomes.includes(c.name)) nomes.push(c.name);
  return nomes;
}

function tocar(nome) {
  clipeAtual = nome;
  pausado = false;
  for (const m of modelos) {
    if (!m.mixer) continue;
    m.mixer.stopAllAction();
    m.mixer.timeScale = 1;
    const c = m.clipes.find((k) => k.name === nome);
    if (c) m.mixer.clipAction(c).reset().play();
  }
  desenharClipes();
}

function repouso() {
  clipeAtual = null;
  for (const m of modelos) {
    m.mixer?.stopAllAction();
    m.raiz.traverse((o) => { if (o.isSkinnedMesh) o.skeleton.pose(); });
  }
  desenharClipes();
}

function desenharClipes() {
  const div = $('clipes');
  const nomes = nomesDeClipes();
  div.hidden = nomes.length === 0;
  div.innerHTML = '<span class="rotulo">clipes</span>';
  for (const n of nomes) {
    const b = document.createElement('button');
    const c = modelos.flatMap((m) => m.clipes).find((k) => k.name === n);
    b.textContent = `▶ ${n} (${c.duration.toFixed(2)} s)`;
    b.classList.toggle('ativo', n === clipeAtual);
    b.onclick = () => tocar(n);
    div.append(b);
  }
  const p = document.createElement('button');
  p.textContent = pausado ? '▶ continuar' : '⏸ pausar';
  p.disabled = !clipeAtual;
  p.onclick = () => {
    pausado = !pausado;
    for (const m of modelos) if (m.mixer) m.mixer.timeScale = pausado ? 0 : 1;
    desenharClipes();
  };
  const r = document.createElement('button');
  r.textContent = 'repouso';
  r.onclick = repouso;
  div.append(p, r);
}

// ---------- câmeras ----------

const cj = config.camera_jogo;
let modoCamera = 'tres_quartos'; // frente | lado | costas | tres_quartos | jogo:<zoom>
let umParaUm = false;

const zoomsDiv = $('zooms-jogo');
for (const z of cj.zooms) {
  const b = document.createElement('button');
  b.dataset.vista = 'jogo:' + z;
  b.textContent = String(z).replace('.', ',');
  b.title = `Câmera do jogo no zoom ${z}: ${(cj.distancia_m / z).toFixed(1)} m, ${cj.inclinacao_graus}°, FOV ${cj.fov_graus}°`;
  zoomsDiv.append(b);
}
$('barra-3d').addEventListener('click', (e) => { if (e.target.dataset.vista) vista(e.target.dataset.vista); });
$('um-para-um').onclick = () => { umParaUm = !umParaUm; ajustarTamanho(); marcarBotoes(); };

function caixaDaCena() {
  const cx = new THREE.Box3();
  for (const m of modelos) cx.expandByObject(m.raiz, true);
  return cx;
}

function vista(qual) {
  modoCamera = qual;
  ajustarTamanho();
  if (qual.startsWith('jogo:')) {
    // CameraRig.cs: câmera a 16 m ÷ zoom do ponto do chão sob o personagem, 55° acima do horizonte, olhando a frente (+Z).
    const d = cj.distancia_m / parseFloat(qual.slice(5));
    const p = deg(cj.inclinacao_graus);
    camera.fov = cj.fov_graus;
    camera.position.set(0, Math.sin(p) * d, Math.cos(p) * d);
    camera.lookAt(0, 0, 0);
    controles.enabled = false;
  } else {
    const cx = caixaDaCena();
    const centro = cx.getCenter(new THREE.Vector3());
    const raio = Math.max(cx.getSize(new THREE.Vector3()).length() / 2, 0.05);
    camera.fov = 30;
    const dist = (raio / Math.sin(deg(camera.fov) / 2)) * 1.05;
    const dir = { frente: [0, 0.08, 1], lado: [1, 0.08, 0], costas: [0, 0.08, -1], tres_quartos: [1, 0.35, 1] }[qual];
    camera.position.copy(centro).add(new THREE.Vector3(...dir).normalize().multiplyScalar(dist));
    controles.target.copy(centro);
    controles.enabled = true;
  }
  camera.updateProjectionMatrix();
  controles.update();
  marcarBotoes();
}

function marcarBotoes() {
  for (const b of $('barra-3d').querySelectorAll('button[data-vista]')) b.classList.toggle('ativo', b.dataset.vista === modoCamera);
  $('um-para-um').hidden = !modoCamera.startsWith('jogo');
  $('um-para-um').classList.toggle('ativo', umParaUm);
}

function ajustarTamanho() {
  const w = caixa3d.clientWidth, h = caixa3d.clientHeight;
  if (!w || !h) return;
  if (modoCamera.startsWith('jogo')) {
    // Resolução de avaliação (3024×1890): desenha nela e encaixa na caixa, ou mostra 1:1 com rolagem.
    const [rw, rh] = cj.resolucao;
    const dpr = window.devicePixelRatio || 1;
    renderer.setPixelRatio(1);
    renderer.setSize(rw, rh, false);
    const k = umParaUm ? 1 / dpr : Math.min(w / rw, h / rh);
    tela.style.width = rw * k + 'px';
    tela.style.height = rh * k + 'px';
    tela.style.margin = umParaUm ? '0' : `${(h - rh * k) / 2}px auto 0`;
    caixa3d.classList.toggle('um-para-um', umParaUm);
    camera.aspect = rw / rh;
  } else {
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    renderer.setSize(w, h, false);
    tela.style.width = w + 'px';
    tela.style.height = h + 'px';
    tela.style.margin = '0';
    caixa3d.classList.remove('um-para-um');
    camera.aspect = w / h;
  }
  camera.updateProjectionMatrix();
}
new ResizeObserver(ajustarTamanho).observe(caixa3d);

// Altura do personagem principal na tela, em pixels da resolução de avaliação (a conta da nota 01).
const _v = new THREE.Vector3();
function medir() {
  const principal = modelos.find((m) => m.principal);
  if (!principal) return;
  const cx = new THREE.Box3().setFromObject(principal.raiz, true);
  const altura = cx.max.y - cx.min.y;
  if (!modoCamera.startsWith('jogo')) {
    $('info-3d').textContent = `altura ${altura.toFixed(3)} m`;
    return;
  }
  // Vértice a vértice (já com a pose do clipe): a caixa envolvente somaria a profundidade à altura.
  let ymin = Infinity, ymax = -Infinity;
  principal.raiz.traverse((o) => {
    if (!o.isMesh || o.material.transparent) return;
    const n = o.geometry.attributes.position.count;
    for (let i = 0; i < n; i++) {
      o.getVertexPosition(i, _v);
      _v.applyMatrix4(o.matrixWorld).project(camera);
      ymin = Math.min(ymin, _v.y); ymax = Math.max(ymax, _v.y);
    }
  });
  const px = ((ymax - ymin) / 2) * cj.resolucao[1];
  $('info-3d').textContent = `altura ${altura.toFixed(3)} m · ${Math.round(px)} px em ${cj.resolucao.join('×')}`;
}

let quadros = 0;
function laco() {
  requestAnimationFrame(laco);
  const dt = relogio.getDelta();
  if (!rodando || caixa3d.hidden) return;
  for (const m of modelos) m.mixer?.update(dt);
  if (controles.enabled) controles.update();
  renderer.render(cena, camera);
  if (quadros++ % 15 === 0) medir();
}
laco();

sondar();
setInterval(sondar, 2000);
