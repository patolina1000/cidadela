// Retalhos do rosto do aldeão ("Olhos" e "Boca"): mostram uma célula do atlas escolhida por instância
// (instance uniform "frame"), com a mesma luz em faixas do corpo (Toon.gdshaderinc), para o rosto escurecer à
// noite junto com ele. Sem sombra projetada, sem contorno. Alpha por mistura (blend_mix), não por recorte: o
// atlas da arte tem olheiras com borda desfocada, e o scissor cortava seco. Sem escrever profundidade
// (depth_draw_never): o retalho fica 1 a 2 mm fora da pele e ainda é testado contra o que é opaco, então o
// cabelo continua escondendo o rosto onde passa na frente. A grade (colunas e linhas) vem do rosto.json; a
// margem transparente já está dentro de cada célula (contrato v2: celulaPx inclui a margem e o retalho mostra a
// célula inteira), então o UV 0..1 do retalho cobre a célula toda e o shader não precisa dela.
shader_type spatial;
render_mode blend_mix, depth_draw_never, cull_back, shadows_disabled, specular_disabled;

#include "res://src/View/Toon.gdshaderinc"

uniform sampler2D atlas : source_color, filter_linear_mipmap, repeat_disable;
uniform int columns = 1;
uniform int rows = 1;
instance uniform int frame = 0;

void fragment() {
	int cols = max(columns, 1);
	int column = frame % cols;
	int row = frame / cols;
	vec2 uv = (UV + vec2(float(column), float(row))) / vec2(float(cols), float(max(rows, 1)));
	vec4 tex = texture(atlas, uv);
	ALBEDO = tex.rgb;
	ALPHA = tex.a;
	ROUGHNESS = 1.0;
	METALLIC = 0.0;
	SPECULAR = 0.0;
}

void light() {
	DIFFUSE_LIGHT += toon_diffuse(NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, ALBEDO);
}
