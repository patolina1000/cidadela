shader_type spatial;
render_mode cull_disabled, depth_draw_opaque;

// Tufos de grama (GDD, seção 17), no espírito de Zelda: Breath of the Wild:
// - base escura que some no chão e ponta clara, para o campo parecer um tapete contínuo;
// - ondas de vento que atravessam o campo como faixas: onde a onda passa, a grama deita e a ponta brilha;
// - tremor pequeno com fase própria por tufo (posição + INSTANCE_CUSTOM.x), para nada mexer igual;
// - a grama se afasta e abaixa em volta da protagonista (pusher_pos, atualizado pela view a cada quadro).
uniform float base_shade = 0.55;
uniform float tip_shade = 1.5;
uniform float wind_strength = 0.02;
uniform float wind_speed = 1.3;
uniform vec2 wind_direction = vec2(0.8, 0.6);
uniform float wave_scale = 0.22;       // tamanho das faixas de vento (menor = faixas mais largas)
uniform float wave_speed = 0.9;        // quão rápido as faixas atravessam o campo (células/s, aprox.)
uniform float wave_strength = 0.05;    // o quanto a onda deita a grama
uniform float wave_sheen = 0.45;       // brilho extra na ponta onde a onda passa
uniform vec3 pusher_pos = vec3(-1000.0);
uniform float push_radius = 0.35;
uniform float push_strength = 0.05;

varying float height_factor;
varying float wave;

float hash(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float value_noise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
		mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

void vertex() {
	// UV.y = 0 na base e 1 na ponta (a malha é gerada assim).
	height_factor = UV.y;
	vec3 world_origin = MODEL_MATRIX[3].xyz;
	vec2 dir = normalize(wind_direction);
	float phase = dot(world_origin.xz, vec2(0.37, 0.61)) + INSTANCE_CUSTOM.x * 6.2832;

	// Faixas de vento: ruído que desliza na direção do vento.
	float n = value_noise(world_origin.xz * wave_scale - dir * TIME * wave_speed * wave_scale);
	wave = smoothstep(0.4, 0.85, n);

	float tremor = sin(TIME * wind_speed * 2.7 + phase) * 0.6 + sin(TIME * wind_speed + phase * 1.7) * 0.4;
	float bend_amount = wind_strength * tremor + wave_strength * wave;
	vec2 bend = dir * bend_amount;

	// Protagonista passando: empurra para fora e abaixa a grama perto dela.
	vec2 away = world_origin.xz - pusher_pos.xz;
	float push = 1.0 - smoothstep(0.0, push_radius, length(away));
	bend += normalize(away + vec2(0.0001)) * push * push_strength;

	float curve = UV.y * UV.y;
	VERTEX.y *= 1.0 - push * 0.45;
	// O deslocamento é no mundo; volta para o espaço do tufo (que tem giro e escala próprios).
	VERTEX += inverse(mat3(MODEL_MATRIX)) * vec3(bend.x * curve, 0.0, bend.y * curve);
	// Normal para cima: o tufo acende como o chão, sem lado escuro.
	NORMAL = inverse(mat3(MODEL_MATRIX)) * vec3(0.0, 1.0, 0.0);
}

void fragment() {
	float shade = mix(base_shade, tip_shade, height_factor);
	shade += wave * wave_sheen * height_factor * height_factor;
	ALBEDO = COLOR.rgb * shade;
	ROUGHNESS = 0.9;
	SPECULAR = 0.15;
}
