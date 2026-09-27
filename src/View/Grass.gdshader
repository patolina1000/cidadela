shader_type spatial;
render_mode cull_disabled;

// Cópia do shader do asset "Stylized Grass Shader" (StayAtHomeDev, MIT; original em assets/grama_stylized),
// com um acréscimo nosso: a grama se inclina para longe da protagonista e abaixa um pouco quando ela passa.
// A view atualiza pusher_pos a cada quadro.

uniform vec3 color : source_color;
uniform vec3 color2 : source_color;
uniform sampler2D noise;
uniform float noiseScale = 20.0;

uniform vec3 pusher_pos = vec3(-1000.0);
uniform float push_radius = 0.45;     // até onde ela mexe na grama, em células
uniform float push_strength = 0.08;   // o quanto a ponta sai do lugar
uniform float grass_height = 0.15;    // altura de referência: a base fica parada, a ponta mexe mais

varying vec3 worldPos;

void vertex() {
	worldPos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;

	vec2 away = MODEL_MATRIX[3].xz - pusher_pos.xz;
	float push = 1.0 - smoothstep(0.0, push_radius, length(away));
	float tip = clamp(worldPos.y / grass_height, 0.0, 1.0);
	tip *= tip;
	vec3 offset = vec3(normalize(away + vec2(0.0001)) * push * push_strength * tip, 0.0).xzy;
	offset.y = -push * 0.4 * worldPos.y;
	// O deslocamento é no mundo; volta para o espaço do tufo (que tem giro e escala próprios).
	VERTEX += inverse(mat3(MODEL_MATRIX)) * offset;
	worldPos += offset;
}

void fragment() {
	vec3 noiseLevel = texture(noise, worldPos.xz / noiseScale).rgb;
	ALBEDO = mix(color, color2, 1.0- UV.y) * mix(color, color2, noiseLevel.r);
	if (!FRONT_FACING) {
		NORMAL = -NORMAL;
	}
}
