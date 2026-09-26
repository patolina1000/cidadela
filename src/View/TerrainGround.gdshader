shader_type spatial;
render_mode cull_disabled;

// Chão natural (GDD, seção 17, "Piso e chão"): cada célula tem um tipo de terreno; as texturas se
// misturam com fronteira orgânica (ruído) e manchas grandes de luz quebram a repetição.
// A grade aparece só no modo construção (grid_strength).

uniform sampler2DArray terrain_textures : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D terrain_map : filter_nearest; // R = índice do terreno da célula / 255
uniform sampler2D noise : repeat_enable, filter_linear;
uniform vec2 map_size = vec2(32.0, 32.0);

uniform float texture_meters = 3.0;   // quantos metros (células) uma repetição da textura cobre
uniform float variant_scale = 0.77;   // segunda amostra da textura, em outra escala (quebra o período)
uniform float variant_noise_scale = 0.07;
uniform float edge_jitter = 0.45;     // quanto a fronteira entre terrenos entorta, em células
uniform float edge_noise_scale = 0.18;
uniform float blend_width = 0.35;     // largura da mistura entre dois terrenos, em células
uniform float macro_strength = 0.12;  // manchas de luz em grande escala
uniform float macro_scale = 0.045;

// Ajuste de cor só do chão (neutro = 1). Serviu para compensar a luz quente antiga; com o crepúsculo
// eterno da cena (26/09/2026) a luz já é fria, e o chão segue a paleta sem correção.
uniform float ground_saturation = 1.0;
uniform vec3 ground_tint : source_color = vec3(1.0, 1.0, 1.0);
uniform float ground_brightness = 1.0;

uniform float grid_strength = 0.0;
uniform vec4 line_color : source_color = vec4(0.0, 0.0, 0.0, 0.35);
uniform float line_width = 0.02;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

float terrain_at(ivec2 cell) {
	cell = clamp(cell, ivec2(0), ivec2(map_size) - 1);
	return floor(texelFetch(terrain_map, cell, 0).r * 255.0 + 0.5);
}

// Duas amostras da mesma textura, em escalas e posições diferentes, alternadas por regiões grandes
// de ruído: o padrão deixa de ter um período fixo (sem isso, manchas da textura formam uma grade).
vec3 terrain_color(float layer, vec2 uv, float variant) {
	vec3 a = texture(terrain_textures, vec3(uv, layer)).rgb;
	vec3 b = texture(terrain_textures, vec3(uv * variant_scale + vec2(0.31, 0.57), layer)).rgb;
	return mix(a, b, variant);
}

void fragment() {
	vec2 p = world_pos.xz;

	// Fronteira orgânica: procura o terreno num ponto entortado por ruído.
	vec2 wobble = vec2(texture(noise, p * edge_noise_scale).r,
			texture(noise, p * edge_noise_scale + vec2(0.37, 0.71)).r) * 2.0 - 1.0;
	vec2 q = p + wobble * edge_jitter - 0.5; // centros das células ficam nos inteiros
	ivec2 c = ivec2(floor(q));
	vec2 f = smoothstep(0.5 - blend_width, 0.5 + blend_width, fract(q));

	float t00 = terrain_at(c);
	float t10 = terrain_at(c + ivec2(1, 0));
	float t01 = terrain_at(c + ivec2(0, 1));
	float t11 = terrain_at(c + ivec2(1, 1));

	vec2 uv = p / texture_meters;
	float variant = smoothstep(0.4, 0.6, texture(noise, p * variant_noise_scale + vec2(0.13, 0.91)).r);
	vec3 color;
	if (t00 == t10 && t00 == t01 && t00 == t11) {
		color = terrain_color(t00, uv, variant);
	} else {
		color = terrain_color(t00, uv, variant) * (1.0 - f.x) * (1.0 - f.y)
			+ terrain_color(t10, uv, variant) * f.x * (1.0 - f.y)
			+ terrain_color(t01, uv, variant) * (1.0 - f.x) * f.y
			+ terrain_color(t11, uv, variant) * f.x * f.y;
	}

	// Manchas grandes de luz: a mesma textura repetida não forma xadrez.
	float macro = texture(noise, p * macro_scale + vec2(0.5, 0.2)).r * 2.0 - 1.0;
	color *= 1.0 + macro * macro_strength;

	float gray = dot(color, vec3(0.299, 0.587, 0.114));
	color = mix(vec3(gray), color, ground_saturation) * ground_tint * ground_brightness;

	// Grade nas bordas das células (só no modo construção).
	vec2 g = fract(p);
	vec2 d = min(g, 1.0 - g);
	vec2 aa = fwidth(p);
	vec2 edge = smoothstep(vec2(line_width) - aa, vec2(line_width) + aa, d);
	float line = (1.0 - min(edge.x, edge.y)) * grid_strength * line_color.a;
	color = mix(color, line_color.rgb, line);

	ALBEDO = color;
	ROUGHNESS = 1.0;
	SPECULAR = 0.2;
}
