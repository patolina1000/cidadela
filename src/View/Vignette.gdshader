shader_type canvas_item;

// Vinheta leve (GDD, seção 17: crepúsculo eterno): escurece as bordas da tela com um roxo profundo.
uniform vec4 tint : source_color = vec4(0.1, 0.07, 0.15, 1.0);
uniform float strength = 0.45;
uniform float inner = 0.42;
uniform float softness = 0.55;

void fragment() {
	vec2 uv = SCREEN_UV - 0.5;
	// Corrige o formato da tela para a vinheta ser redonda, não oval.
	uv.x *= SCREEN_PIXEL_SIZE.y / SCREEN_PIXEL_SIZE.x;
	float edge = smoothstep(inner, inner + softness, length(uv));
	COLOR = vec4(tint.rgb, edge * strength);
}
