shader_type spatial;
render_mode cull_disabled;

uniform vec4 base_color : source_color = vec4(0.48, 0.55, 0.35, 1.0);
uniform vec4 line_color : source_color = vec4(0.36, 0.42, 0.26, 1.0);
uniform float line_width = 0.025;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	// Linhas nas coordenadas inteiras do mundo = bordas das células.
	vec2 f = fract(world_pos.xz);
	vec2 d = min(f, 1.0 - f);
	vec2 aa = fwidth(world_pos.xz);
	vec2 edge = smoothstep(vec2(line_width) - aa, vec2(line_width) + aa, d);
	float line = 1.0 - min(edge.x, edge.y);
	ALBEDO = mix(base_color.rgb, line_color.rgb, line);
	ROUGHNESS = 1.0;
}
