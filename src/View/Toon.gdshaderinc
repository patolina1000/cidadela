// Luz em faixas (toon) compartilhada por corpo, cabelo e rosto do aldeão: quem usa esta função escurece
// igual sob a mesma luz. Sem contorno por enquanto (GDD, seção 17; fica para tarefa própria).
// Uso, no shader: void light() { DIFFUSE_LIGHT += toon_diffuse(NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, ALBEDO); }

const int TOON_STEPS = 3;
const float TOON_SHADOW_FLOOR = 0.35; // a faixa mais escura da luz direta ainda deixa ver a cor

vec3 toon_diffuse(vec3 normal, vec3 light_dir, vec3 light_color, float attenuation, vec3 albedo) {
	// Meio-Lambert: o lado oposto à luz não fica preto, só na faixa de baixo.
	float ndl = clamp(dot(normal, light_dir) * 0.5 + 0.5, 0.0, 1.0);
	float band = floor(ndl * float(TOON_STEPS)) / float(TOON_STEPS - 1);
	band = mix(TOON_SHADOW_FLOOR, 1.0, clamp(band, 0.0, 1.0));
	return albedo * light_color * attenuation * band;
}
