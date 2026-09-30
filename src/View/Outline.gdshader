// Contorno fino escuro (GDD, seção 17: "toon com contorno fino escuro, lembrando Castle Crashers"), como segundo passe
// (next_pass) do material: uma casca invertida (só as faces de trás) empurrada para fora pela normal no espaço de
// recorte, então a espessura fica constante em pixels em qualquer zoom. Vale para MultiMesh (o passe vai junto da malha
// instanciada) e para personagens animados (o empurrão é depois do esqueleto). Não projeta sombra. O recorte em volta
// da protagonista (Toon.gdshaderinc) vale aqui também, para o contorno da copa não aparecer no buraco.
shader_type spatial;
render_mode unshaded, cull_front, depth_draw_opaque, shadows_disabled, specular_disabled;

#include "res://src/View/Toon.gdshaderinc"

uniform vec4 outline_color : source_color = vec4(0.106, 0.086, 0.125, 1.0);
uniform float width_px = 1.5;
uniform float reference_height = 1890.0;

void vertex() {
	vec4 clip = PROJECTION_MATRIX * (MODELVIEW_MATRIX * vec4(VERTEX, 1.0));
	vec3 n = normalize((MODELVIEW_MATRIX * vec4(NORMAL, 0.0)).xyz);
	vec2 dir = (PROJECTION_MATRIX * vec4(n, 0.0)).xy;
	float len = length(dir);
	if (len > 1e-5) {
		dir /= len;
	}
	float px = width_px * VIEWPORT_SIZE.y / reference_height;
	clip.xy += dir * px * 2.0 / VIEWPORT_SIZE * clip.w;
	POSITION = clip;
}

void fragment() {
	if (toon_occluded(VERTEX, FRAGCOORD.xy, VIEW_MATRIX, PROJECTION_MATRIX)) {
		discard;
	}
	ALBEDO = outline_color.rgb;
}
