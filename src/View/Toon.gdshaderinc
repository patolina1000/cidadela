// Luz em faixas (toon) compartilhada por corpo, cabelo e rosto do aldeão: quem usa esta função escurece
// igual sob a mesma luz. Sem contorno por enquanto (GDD, seção 17; fica para tarefa própria).
// Uso, no shader: void light() { DIFFUSE_LIGHT += toon_diffuse(NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, ALBEDO); }
// Borda de luz fria (fresnel em faixa dura), desligada por padrão: o aldeão fica como está. Ligada nos objetos de
// cenário (e, pelo contrato, na protagonista v2). Uso: EMISSION += toon_rim(NORMAL, VIEW); os valores vêm de
// data/visual.json, postos no material pelo código.

const int TOON_STEPS = 3;
const float TOON_SHADOW_FLOOR = 0.35; // a faixa mais escura da luz direta ainda deixa ver a cor

vec3 toon_diffuse(vec3 normal, vec3 light_dir, vec3 light_color, float attenuation, vec3 albedo) {
	// Meio-Lambert: o lado oposto à luz não fica preto, só na faixa de baixo.
	float ndl = clamp(dot(normal, light_dir) * 0.5 + 0.5, 0.0, 1.0);
	float band = floor(ndl * float(TOON_STEPS)) / float(TOON_STEPS - 1);
	band = mix(TOON_SHADOW_FLOOR, 1.0, clamp(band, 0.0, 1.0));
	return albedo * light_color * attenuation * band;
}

uniform bool rim_enabled = false;
uniform vec3 rim_color : source_color = vec3(0.72, 0.78, 0.9); // a cor do sol frio do Main.tscn
uniform float rim_strength = 0.1;
uniform float rim_width = 0.144; // acende onde |N·V| fica abaixo disto (a silhueta vista de lado)

vec3 toon_rim(vec3 normal, vec3 view) {
	if (!rim_enabled) {
		return vec3(0.0);
	}
	float facing = abs(dot(normal, view));
	return rim_color * rim_strength * step(facing, rim_width);
}
