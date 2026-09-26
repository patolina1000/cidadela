shader_type spatial;
render_mode cull_disabled, depth_draw_opaque;

// Tufos de grama (GDD, seção 17): cor por tufo (cor da instância), ponta mais clara que a base,
// e balanço de vento que cresce para a ponta. Cada tufo tem sua fase (posição no mundo + um valor
// aleatório em INSTANCE_CUSTOM.x), então a grama não mexe toda junto.
uniform float base_shade = 1.0;
uniform float tip_shade = 1.6;
uniform float wind_strength = 0.045;
uniform float wind_speed = 1.3;
uniform vec2 wind_direction = vec2(0.8, 0.6);

varying float height_factor;

void vertex() {
	// UV.y = 0 na base e 1 na ponta (a malha é gerada assim).
	height_factor = UV.y;
	vec3 world_origin = MODEL_MATRIX[3].xyz;
	float phase = dot(world_origin.xz, vec2(0.37, 0.61)) + INSTANCE_CUSTOM.x * 6.2832;
	// Duas ondas: uma lenta e larga (rajada que passa pelo campo) e uma rápida e pequena (tremor).
	float gust = sin(TIME * wind_speed * 0.45 + dot(world_origin.xz, wind_direction) * 0.25) * 0.5 + 0.5;
	float sway = sin(TIME * wind_speed + phase) * (0.35 + 0.65 * gust);
	sway += sin(TIME * wind_speed * 2.7 + phase * 1.7) * 0.25;
	vec2 bend = normalize(wind_direction) * sway * wind_strength * UV.y * UV.y;
	// O deslocamento é no mundo; volta para o espaço do tufo (que tem giro e escala próprios).
	VERTEX += inverse(mat3(MODEL_MATRIX)) * vec3(bend.x, 0.0, bend.y);
	// Normal para cima: o tufo acende como o chão, sem lado escuro.
	NORMAL = inverse(mat3(MODEL_MATRIX)) * vec3(0.0, 1.0, 0.0);
}

void fragment() {
	float shade = mix(base_shade, tip_shade, height_factor);
	ALBEDO = COLOR.rgb * shade;
	ROUGHNESS = 0.95;
	SPECULAR = 0.1;
}
