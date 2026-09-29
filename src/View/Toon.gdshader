// Corpo e cabelo do aldeão: cor chapada com luz em faixas (Toon.gdshaderinc). Um material por cor.
shader_type spatial;
render_mode cull_back, depth_draw_opaque, specular_disabled;

#include "res://src/View/Toon.gdshaderinc"

uniform vec4 albedo : source_color = vec4(1.0);

void fragment() {
	ALBEDO = albedo.rgb;
	ROUGHNESS = 0.95;
	METALLIC = 0.0;
	SPECULAR = 0.0;
}

void light() {
	DIFFUSE_LIGHT += toon_diffuse(NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, ALBEDO);
}
