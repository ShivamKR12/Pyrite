import pygame as pg
import moderngl as mgl


class Textures:
    def __init__(self, app):
        self.app = app
        self.ctx = app.ctx

        # load textures
        self.texture_0 = self.load('frame.png')
        self.texture_array_0 = self.load('tex_array_2.png', is_tex_array=True)
        self.texture_breaking = self.load('block_breaking_texture.png')
        self.texture_stick = self.load('stick.png')
        self.texture_pickaxe = self.load('wooden_pickaxe.png', rotation=-90)

        # assign texture unit
        self.texture_0.use(location=0)
        self.texture_array_0.use(location=1)
        self.texture_breaking.use(location=3)
        self.texture_stick.use(location=5)
        self.texture_pickaxe.use(location=6)

    def load(self, file_name, is_tex_array=False, rotation=0):
        texture = pg.image.load(f'assets/{file_name}')
        if rotation != 0:
            texture = pg.transform.rotate(texture, rotation)
        texture = pg.transform.flip(texture, flip_x=True, flip_y=False)

        if is_tex_array:
            num_layers = 3 * texture.get_height() // texture.get_width()  # 3 textures per layer
            texture = self.app.ctx.texture_array(
                size=(texture.get_width(), texture.get_height() // num_layers, num_layers),
                components=4,
                data=pg.image.tostring(texture, 'RGBA')
            )
        else:
            texture = self.ctx.texture(
                size=texture.get_size(),
                components=4,
                data=pg.image.tostring(texture, 'RGBA', False)
            )
        texture.anisotropy = 32.0
        texture.build_mipmaps()
        texture.filter = (mgl.NEAREST, mgl.NEAREST)
        return texture
