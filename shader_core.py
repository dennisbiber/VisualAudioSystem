import moderngl
import numpy as np
import math
import cv2
import time

class VisualSynthRenderer:
    """
    Renderer is now stateless.

    It does NOT store parameters.
    It simply reads the modulator every frame.

    One truth. One state.
    """

    def __init__(self, mod):

        self.mod = mod
        self.ctx = moderngl.create_context()

        self.prog = self.ctx.program(
            vertex_shader=self._vertex_shader(),
            fragment_shader=self._fragment_shader()
        )

        quad = self.ctx.buffer(
            np.array([-1, -1, 1, -1, -1, 1, 1, 1], dtype='f4')
        )

        self.vao = self.ctx.simple_vertex_array(
            self.prog,
            quad,
            "in_vert"
        )

        self.bg_tex_current = None
        self.bg_tex_next = None

        self.bg_video = None
        self.bg_video_next = None

        self.video_speed = self.mod.state.get("video_speed", 1.0)
        self.video_time = 0.0

        self.transition_active = False
        self.transition_start = 0.0
        self.transition_duration = 1.0
        self.transition_mode = "fade"  # or "instant"

        self.backgrounds = self.mod.state.get("background_list", [])

        # load initial
        if self.backgrounds:
            self._load_background(self.backgrounds[0], initial=True)

    def _load_texture(self, path):
        from PIL import Image

        img = Image.open(path).convert("RGB").transpose(Image.FLIP_TOP_BOTTOM)

        tex = self.ctx.texture(img.size, 3, img.tobytes())
        tex.build_mipmaps()
        tex.repeat_x = True
        tex.repeat_y = True
        tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)

        return tex

    def _load_background(self, path, initial=False):
        ext = path.split(".")[-1].lower()

        if ext in ["jpg", "png", "jpeg", "bmp"]:
            tex = self._load_texture(path)
            video = None
        else:
            video = cv2.VideoCapture(path)
            tex = self._create_empty_texture()
        
        if initial:
            self.bg_tex_current = tex
            self.bg_video = video
        else:
            self.bg_tex_next = tex
            self.bg_video_next = video
            self._start_transition()

    def _create_empty_texture(self):
        tex = self.ctx.texture((1280, 720), 3)
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        tex.repeat_x = True
        tex.repeat_y = True
        return tex
    
    def _start_transition(self):
        self.transition_mode = self.mod.state.get("bg_transition_mode", "fade")
        self.transition_duration = self.mod.state.get("bg_transition_time", 1.0)

        if self.transition_mode == "instant":
            self._complete_transition()
        else:
            self.transition_active = True
            self.transition_start = time.time()

    def _complete_transition(self):
        if self.bg_video:
            self.bg_video.release()

        self.bg_tex_current = self.bg_tex_next
        self.bg_video = self.bg_video_next

        self.bg_tex_next = None
        self.bg_video_next = None
        self.transition_active = False

    def _update_video(self, video, texture, dt):
        if not video:
            return texture

        fps = video.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0  # fallback safety

        frame_count = video.get(cv2.CAP_PROP_FRAME_COUNT)

        # advance internal video clock
        self.video_time += dt * self.video_speed

        # loop video
        duration = frame_count / fps
        if duration > 0:
            self.video_time = self.video_time % duration

        # compute frame index
        frame_index = int(self.video_time * fps)

        video.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

        ret, frame = video.read()
        if not ret:
            return texture

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.flip(frame, 0)

        h, w, _ = frame.shape

        if texture.size != (w, h):
            texture.release()
            texture = self.ctx.texture((w, h), 3)

        texture.write(frame.tobytes())

        return texture
    
    def set_video_speed(self, value):
        self.video_speed = max(0.0, value)

    def adjust_video_speed(self, delta):
        self.video_speed = max(0.0, self.video_speed + delta)

    def set_background(self, index):
        if index < 0 or index >= len(self.backgrounds):
            return

        path = self.backgrounds[index]
        self._load_background(path)


    # =================================================
    # SHADERS (unchanged)
    # =================================================

    def _vertex_shader(self):
        return """
        #version 330
        in vec2 in_vert;
        out vec2 uv;

        void main() {
            uv = in_vert * 0.5 + 0.5;
            gl_Position = vec4(in_vert, 0.0, 1.0);
        }
        """

    # (fragment shader EXACTLY same as yours — no change needed)


    # -------------------------------------------------

    def _fragment_shader(self):
        return """
        #version 330

        uniform float time;
        uniform vec2 resolution;

        uniform vec2 drift;
        uniform float density;
        uniform float energy;
        uniform float brightness;

        uniform float base_hue;
        uniform float layer_hue;
        uniform float color_pan;
        uniform float color_mod_enabled;

        uniform float warp_strength;
        uniform vec2 warp_center;
        uniform float strobe;

        uniform float stars;
        uniform float aurora;
        uniform float lightning;
        uniform float particles;

        uniform sampler2D bg_tex_current;
        uniform sampler2D bg_tex_next;
        uniform float bg_mix;
        uniform float bg_transition;
        uniform float bg_scroll;
        uniform float bg_zoom;

        in vec2 uv;
        out vec4 fragColor;

        // ============================================
        // utilities
        // ============================================

        float hash(vec2 p){
            return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);
        }

        float noise(vec2 p){
            vec2 i=floor(p);
            vec2 f=fract(p);

            float a=hash(i);
            float b=hash(i+vec2(1,0));
            float c=hash(i+vec2(0,1));
            float d=hash(i+vec2(1,1));

            vec2 u=f*f*(3.-2.*f);

            return mix(a,b,u.x) +
                   (c-a)*u.y*(1.-u.x) +
                   (d-b)*u.x*u.y;
        }

        vec3 hsv2rgb(vec3 c){
            vec3 p = abs(fract(c.xxx + vec3(0,2./3.,1./3.))*6.-3.);
            return c.z * mix(vec3(1.), clamp(p-1.,0.,1.), c.y);
        }

        vec3 palette(float t){
            return 0.5 + 0.5*cos(6.28318*(vec3(0.0,0.33,0.66)+t));
        }

        vec2 warp(vec2 uv){
            vec2 d = uv - warp_center;
            float r = length(d);
            r = pow(r, 1.0 - warp_strength);
            return warp_center + normalize(d) * r;
        }

        // ============================================

        float layer(vec2 p, float scale, float speed){
            p *= scale;
            p += drift * speed * time;
            return smoothstep(0.55, 0.75, noise(p));
        }

        // ============================================

        void main(){

            vec2 p = warp(uv);

            // -------- base gradient ----------
            vec3 top = hsv2rgb(vec3(base_hue, 0.4, 1.0));
            vec3 bottom = hsv2rgb(vec3(base_hue + 0.05, 0.6, 0.7));

            vec3 col;

            vec3 procedural = mix(bottom, top, p.y);

            vec3 bg = procedural;

            if(bg_mix > 0.0){
                vec2 uv_bg = (p - 0.5) * bg_zoom + 0.5 + drift * bg_scroll;
                vec3 bg1 = texture(bg_tex_current, uv_bg).rgb;
                vec3 bg2 = texture(bg_tex_next, uv_bg).rgb;
                bg = mix(bg1, bg2, bg_transition);
            }
            col = mix(procedural, bg, bg_mix);


            // -------- layered noise ----------
            float n =
                layer(p, 2.0, 0.2) * 0.4 +
                layer(p, 4.0, 0.5) * 0.7 +
                layer(p, 7.0, 1.0);

            n *= density;

            vec3 layer_col = hsv2rgb(vec3(layer_hue, 0.2, 1.0));

            col = mix(col, layer_col, n);

            // -------- stars ----------
            if(stars > 0.5){
                float s = step(0.996, hash(floor(p*400.0)));
                col += s * 1.2;
            }

            // -------- aurora band ----------
            if(aurora > 0.5){
                float band = sin(p.x*6. + time*0.4) * 0.5 + 0.5;
                float m = smoothstep(0.4,0.7,band*noise(p*6.));
                col += vec3(0.1,0.8,0.5) * m * energy;
            }

            // -------- lightning ----------
            if(lightning > 0.01){
                float bolt = 0.02 / (abs(p.x - 0.5) + 0.01);
                col += vec3(0.7,0.9,1.0) * bolt * lightning;
            }

            // -------- color modulation ----------
            vec3 modulated = col * palette(color_pan);
            col = mix(col, modulated, color_mod_enabled);

            // -------- strobe ----------
            float st = mix(1.0, step(0.5, fract(time*8.0)), strobe);
            col *= st;

            fragColor = vec4(col * brightness, 1.0);
        }
        """

    # =================================================
    # runtime control
    # =================================================

    def set(self, **kwargs):
        """Update synth parameters live."""
        self.params.update(kwargs)

    # -------------------------------------------------

    def render(self):
        s = self.mod.state

        # -----------------------------------------
        # derived values (computed fresh every frame)
        # -----------------------------------------
        # set varables
        speed = s.get("current_speed", 0.0)
        angle = s.get("wind_angle", 0.0)
        dt = s.get("dt", 0.016)

        # Update videos
        if self.bg_video:
            self.bg_tex_current = self._update_video(self.bg_video, self.bg_tex_current, dt)

        if self.bg_video_next:
            self.bg_tex_next = self._update_video(self.bg_video_next, self.bg_tex_next, dt)

        transition_value = 0.0

        if self.transition_active:
            elapsed = time.time() - self.transition_start
            transition_value = min(1.0, elapsed / self.transition_duration)

            if transition_value >= 1.0:
                self._complete_transition()

        # update modulations
        drift = (
            math.cos(angle) * speed,
            math.sin(angle) * speed
        )

        warp_center = (
            s.get("warp_x", 0.5),
            s.get("warp_y", 0.5)
        )

        # -----------------------------------------
        # uniform mapping
        # -----------------------------------------

        mapping = {
            "time": s["time"],
            "brightness": s["brightness"],
            "density": s["cloud_density"],
            "energy": s["energy"],

            "base_hue": s["base_hue"],
            "layer_hue": s["layer_hue"],
            "color_pan": s["color_pan"],

            "strobe": s["strobe"],
            "aurora": s["aurora"],
            "lightning": s["lightning"],
            "color_mod_enabled": s.get("color_mod_enabled", 1.0),

            "drift": drift,
            "warp_center": warp_center,
            "warp_strength": s.get("warp_strength", 0.0),
            "bg_mix": s.get("bg_mix", 0.0),
            "bg_scroll": s.get("bg_scroll", 0.0),
            "bg_zoom": s.get("bg_zoom", 1.0),
        }

        # -----------------------------------------
        # push uniforms
        # -----------------------------------------

        if self.bg_tex_current:
            self.bg_tex_current.use(0)
            self.prog["bg_tex_current"] = 0

        if self.bg_tex_next:
            self.bg_tex_next.use(1)
            self.prog["bg_tex_next"] = 1

        self.prog["bg_transition"].value = transition_value


        for name, value in mapping.items():
            if name in self.prog:
                self.prog[name].value = value

        # -----------------------------------------
        # draw
        # -----------------------------------------

        self.ctx.clear()
        self.vao.render(moderngl.TRIANGLE_STRIP)



