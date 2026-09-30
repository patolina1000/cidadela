// Barra de progresso da receita sobre a máquina (EnergyOverlay.cs): um quadrado virado para a câmera, preenchido da
// esquerda até "progress". Sem PROJECTION_MATRIX (o sinal dele muda entre Vulkan e Metal).
shader_type spatial;
render_mode unshaded, cull_disabled, depth_test_disabled, shadows_disabled;

instance uniform float progress = 0.0;
uniform vec4 fill_color : source_color = vec4(0.72, 0.78, 0.9, 1.0);
uniform vec4 back_color : source_color = vec4(0.1, 0.08, 0.13, 0.85);

void vertex() {
	// Billboard: os eixos da câmera, com a escala do nó.
	MODELVIEW_MATRIX = VIEW_MATRIX * mat4(
		INV_VIEW_MATRIX[0] * length(MODEL_MATRIX[0].xyz),
		INV_VIEW_MATRIX[1] * length(MODEL_MATRIX[1].xyz),
		INV_VIEW_MATRIX[2],
		MODEL_MATRIX[3]);
}

void fragment() {
	bool border = UV.y < 0.12 || UV.y > 0.88 || UV.x < 0.02 || UV.x > 0.98;
	vec4 c = (!border && UV.x < progress) ? fill_color : back_color;
	ALBEDO = c.rgb;
	ALPHA = c.a;
}
