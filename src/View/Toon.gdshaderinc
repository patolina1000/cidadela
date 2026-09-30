// Luz em faixas (toon) compartilhada por corpo, cabelo e rosto do aldeão: quem usa esta função escurece
// igual sob a mesma luz. Sem contorno por enquanto (GDD, seção 17; fica para tarefa própria).
// Uso, no shader: void light() { DIFFUSE_LIGHT += toon_diffuse(NORMAL, LIGHT, LIGHT_COLOR, ATTENUATION, ALBEDO); }
// Borda de luz fria (fresnel em faixa dura), desligada por padrão: o aldeão fica como está. Ligada nos objetos de
// cenário (e, pelo contrato, na protagonista v2). Uso: EMISSION += toon_rim(NORMAL, VIEW); os valores vêm de
// data/visual.json, postos no material pelo código.
// Esmaecer o que tapa personagem: com "occlusion_enabled", o que fica entre a câmera e a protagonista, num círculo
// em volta dela, é recortado em pontilhado (screen-door). Uso, no fragment: if (toon_occluded(VERTEX, FRAGCOORD.xy,
// VIEW_MATRIX, PROJECTION_MATRIX)) discard; O código põe o centro (o peito dela) no material a cada quadro.

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

uniform bool occlusion_enabled = false;
uniform vec3 occlusion_center = vec3(0.0); // peito da protagonista, no mundo
uniform float occlusion_radius = 0.6;      // metros, na distância dela
uniform float occlusion_keep = 0.35;       // fração dos pixels que ficam no miolo do círculo
uniform float occlusion_softness = 0.3;    // fração do raio em que volta a ficar inteiro

// Limiar do pontilhado Bayer 4×4 (0..1) do pixel.
float toon_bayer4(vec2 frag_coord) {
	ivec2 p = ivec2(mod(frag_coord, 4.0));
	int i = p.x + p.y * 4;
	int m[16] = int[](0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5);
	return (float(m[i]) + 0.5) / 16.0;
}

bool toon_occluded(vec3 view_vertex, vec2 frag_coord, mat4 view_matrix, mat4 projection) {
	// Projeção ortográfica = sombra do sol: a sombra fica inteira.
	if (!occlusion_enabled || projection[3][3] != 0.0) {
		return false;
	}
	vec3 center = (view_matrix * vec4(occlusion_center, 1.0)).xyz;
	float center_depth = -center.z;
	float depth = -view_vertex.z;
	// Só o que está na frente dela (com folga para não recortar o que está do lado).
	if (center_depth <= 0.0 || depth > center_depth - 0.3) {
		return false;
	}
	// Distância do raio do pixel ao centro, medida na profundidade dela: o círculo tem o mesmo tamanho em metros.
	vec2 offset = view_vertex.xy / depth - center.xy / center_depth;
	float d = length(offset) * center_depth / occlusion_radius;
	if (d >= 1.0) {
		return false;
	}
	float keep = mix(occlusion_keep, 1.0, smoothstep(1.0 - occlusion_softness, 1.0, d));
	return toon_bayer4(frag_coord) > keep;
}
