// Cor chapada com luz em faixas (Toon.gdshaderinc): corpo e cabelo do aldeão e os recursos do mapa. Um material por
// cor; a cor pode variar por instância pelo "tint" (os tons de cabelo de data/villager_looks.json), sem duplicar
// material. A borda de luz fria só acende onde o material liga "rim_enabled" (os recursos).
shader_type spatial;
render_mode cull_back, depth_draw_opaque, specular_disabled;

#include "res://src/View/Toon.gdshaderinc"

uniform vec4 albedo : source_color = vec4(1.0);
instance uniform vec4 tint : source_color = vec4(1.0);

void fragment() {
	ALBEDO = albedo.rgb * tint.rgb;
	ROUGHNESS = 0.95;
	METALLIC = 0.0;
	SPECULAR = 0.0;
	EMISSION = toon_rim(NORMAL, VIEW);
}

void light() {
	DIFFUSE_LIGHT += toon_diffuse(NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, ALBEDO);
}
