// Ícone de estado sobre a cabeça do aldeão (VillagerIcons.cs): um quadrado virado para a câmera, preso pela base num
// ponto acima da cabeça e crescendo para cima, para nunca tapar o rosto. O tamanho é fixo em pixels (entre
// min_px e max_px na altura de referência), para ler do zoom 0,4 ao 2,5. Todos os ícones num MultiMesh: a célula do
// atlas vem por instância (INSTANCE_CUSTOM.x). Sem luz, sem névoa e por cima de tudo (é informação).
shader_type spatial;
render_mode unshaded, depth_test_disabled, depth_draw_never, cull_disabled, blend_mix, shadows_disabled, fog_disabled;

uniform sampler2D atlas : source_color, filter_linear_mipmap, repeat_disable;
uniform float cells = 1.0;
uniform float world_size = 0.3;
uniform float min_px = 26.0;
uniform float max_px = 44.0;
uniform float reference_height = 1890.0;

varying float v_cell;

void vertex() {
	vec4 anchor = MODELVIEW_MATRIX * vec4(0.0, 0.0, 0.0, 1.0);
	float depth = max(-anchor.z, 0.01);
	float px_per_m = PROJECTION_MATRIX[1][1] * 0.5 * VIEWPORT_SIZE.y / depth;
	float scale = VIEWPORT_SIZE.y / reference_height;
	float px = clamp(world_size * px_per_m, min_px * scale, max_px * scale);
	// O QuadMesh vai de -0,5 a 0,5: a base sobe para o ponto de ancoragem.
	vec2 offset = (VERTEX.xy + vec2(0.0, 0.5)) * (px / px_per_m);
	POSITION = PROJECTION_MATRIX * vec4(anchor.xyz + vec3(offset, 0.0), 1.0);
	v_cell = INSTANCE_CUSTOM.x;
}

void fragment() {
	vec4 c = texture(atlas, vec2((UV.x + v_cell) / cells, UV.y));
	ALBEDO = c.rgb;
	ALPHA = c.a;
}
