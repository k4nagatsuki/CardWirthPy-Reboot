#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base

import cw


class BgImage(base.CWBinaryBase):
    """背景のセルデータ。"""
    def __init__(self, parent, f, yadodata=False):
        base.CWBinaryBase.__init__(self, parent, f, yadodata)
        self.left = f.dword()
        self.top = f.dword()
        self.width = f.dword()
        if self.width <= 39999:
            dataversion = 2
        elif self.width <= 49999:
            dataversion = 4
            self.width -= 40000
        elif self.width <= 59999:
            dataversion = 5
            self.width -= 50000
        else:
            dataversion = 6
            self.width -= 60000
        self.height = f.dword()
        if dataversion <= 5:
            self.type = cw.sprite.background.BG_IMAGE
            self.imgpath = f.string()
            self.mask = f.bool()
            if 2 < dataversion:
                self.flag = f.string()
                self.unknown = f.byte()
            else:
                self.flag = ""
                self.unknown = 0
        else:
            bgtype = f.byte()
            if bgtype == 2:
                # テキストセル
                self.type = cw.sprite.background.BG_TEXT
                self.mask = f.bool()
                self.text = f.string(True)
                self.fontface = f.string()
                self.fontsize = f.dword()
                r = f.ubyte()
                g = f.ubyte()
                b = f.ubyte()
                a = f.ubyte()
                self.color = (r, g, b, a)
                style = f.byte()
                self.bold      = (style & 0b00000001) <> 0
                self.italic    = (style & 0b00000010) <> 0
                self.underline = (style & 0b00000100) <> 0
                self.strike    = (style & 0b00001000) <> 0
                self.bordering = (style & 0b00010000) <> 0
                self.vertical  = (style & 0b00100000) <> 0
                if self.bordering:
                    self.btype = f.byte()
                    r = f.ubyte()
                    g = f.ubyte()
                    b = f.ubyte()
                    a = f.ubyte()
                    self.bcolor = (r, g, b, a)
                    self.bwidth = f.dword()
                else:
                    self.btype = -1
                    self.bcolor = (255, 255, 255, 255)
                    self.bwidth = 1
                f.byte() # 不明(100)
                f.dword() # 不明(0)
                f.dword() # 不明(0)
                f.byte() # 不明(縦書き時:2,他:0)
                self.flag = f.string()
                self.unknown = f.byte()

            elif bgtype == 3:
                # カラーセル
                self.type = cw.sprite.background.BG_COLOR
                self.blend = f.byte()
                self.gradient = f.byte()
                b = f.ubyte() # RGBの順序が逆
                g = f.ubyte()
                r = f.ubyte()
                a = f.ubyte()
                self.color1 = (r, g, b, a)
                if self.gradient <> 0:
                    b = f.ubyte() # RGBの順序が逆
                    g = f.ubyte()
                    r = f.ubyte()
                    a = f.ubyte()
                    self.color2 = (r, g, b, a)
                else:
                    self.color2 = (255, 255, 255, 255)
                self.flag = f.string()
                self.unknown = f.byte()

            else:
                raise ValueError("Background type: %s" % (bgtype))

        self.data = None

    def get_data(self):
        if self.data is None:
            def makecolor(tag, color):
                return cw.data.make_element(tag, attrs={"r":str(color[0]),
                                                        "g":str(color[1]),
                                                        "b":str(color[2]),
                                                        "a":str(color[3])})

            if self.type == cw.sprite.background.BG_IMAGE:
                self.data = cw.data.make_element("BgImage")
                self.data.set("mask", str(self.mask))
                e = cw.data.make_element("ImagePath", self.get_materialpath(self.imgpath))
                self.data.append(e)

            elif self.type == cw.sprite.background.BG_TEXT:
                self.data = cw.data.make_element("TextCell")

                e = cw.data.make_element("Text", self.text)
                self.data.append(e)
                e = cw.data.make_element("Font", self.fontface, attrs={"size": str(self.fontsize),
                                                                       "bold": str(self.bold),
                                                                       "italic": str(self.italic),
                                                                       "underline": str(self.underline),
                                                                       "strike": str(self.strike)})
                self.data.append(e)
                e = cw.data.make_element("Vertical", str(self.vertical))
                self.data.append(e)
                e = makecolor("Color", self.color)
                self.data.append(e)

                if self.bordering:
                    btype = self.conv_borderingtype(self.btype)
                    e = cw.data.make_element("Bordering", attrs={"type": btype,
                                                                 "width": str(self.bwidth)})
                    e.append(makecolor("Color", self.bcolor))
                    self.data.append(e)

            elif self.type == cw.sprite.background.BG_COLOR:
                self.data = cw.data.make_element("ColorCell")

                e = cw.data.make_element("BlendMode", self.conv_blendmode(self.blend))
                self.data.append(e)
                e = makecolor("Color", self.color1)
                self.data.append(e)

                if self.gradient <> 0:
                    dire = self.conv_gradientdir(self.gradient)
                    e = cw.data.make_element("Gradient", attrs={"direction": dire})
                    e.append(makecolor("EndColor", self.color2))
                    self.data.append(e)

            e = cw.data.make_element("Flag", self.flag)
            self.data.append(e)
            e = cw.data.make_element("Location")
            e.set("left", str(self.left))
            e.set("top", str(self.top))
            self.data.append(e)
            e = cw.data.make_element("Size")
            e.set("width", str(self.width))
            e.set("height", str(self.height))
            self.data.append(e)
        return self.data

    @staticmethod
    def unconv(f, data):
        left = 0
        top = 0
        width = 0
        height = 0
        flag = ""
        unknown = 0

        if data.get("cellname", ""):
            f.check_wsnversion("1")

        # 背景画像
        imgpath = ""
        mask = cw.util.str2bool(data.get("mask", False))

        # テキストセル
        text = ""
        fontface = ""
        fontsize = 12
        color = (0, 0, 0, 255)
        bold = False
        italic = False
        underline = False
        strike = False
        vertical = False
        btype = -1
        bcolor = (255, 255, 255, 255)
        bwidth = 1

        # カラーセル
        blend = 0
        color1 = (255, 255, 255, 255)
        gradient = 0
        color2 = (0, 0, 0, 255)

        def getcolor(e, defcolor):
            r = int(e.get("r", str(defcolor[0])))
            g = int(e.get("g", str(defcolor[1])))
            b = int(e.get("b", str(defcolor[2])))
            a = int(e.get("a", str(defcolor[3])))
            return (r, g, b, a)

        for e in data:
            if e.tag == "Flag":
                flag = e.text
            elif e.tag == "Location":
                left = int(e.get("left"))
                top = int(e.get("top"))
            elif e.tag == "Size":
                width = int(e.get("width"))
                height = int(e.get("height"))

            elif data.tag == "BgImage":
                if e.tag == "ImagePath":
                    imgpath = e.text

            elif data.tag == "TextCell":
                f.check_version(1.50)
                if e.tag == "Text":
                    text = e.text
                elif e.tag == "Font":
                    fontface = e.text
                    fontsize = int(e.get("size", fontsize))
                    for e_font in e:
                        if e_font.tag == "Color":
                            color = getcolor(e_font, color)
                    bold = cw.util.str2bool(e.get("bold", bold))
                    italic = cw.util.str2bool(e.get("italic", italic))
                    underline = cw.util.str2bool(e.get("underline", underline))
                    strike = cw.util.str2bool(e.get("strike", strike))
                elif e.tag == "Vertical":
                    vertical = cw.util.str2bool(e.text)
                elif e.tag == "Bordering":
                    btype = base.CWBinaryBase.unconv_borderingtype(e.get("type", "None"))
                    bwidth = int(e.get("width", "1"))
                    for e_bdr in e:
                        if e_bdr.tag == "Color":
                            bcolor = getcolor(e_bdr, bcolor)

            elif data.tag == "ColorCell":
                f.check_version(1.50)
                if e.tag == "BlendMode":
                    blend = base.CWBinaryBase.unconv_blendmode(e.text)
                elif e.tag == "Color":
                    color1 = getcolor(e, color1)
                elif e.tag == "Gradient":
                    gradient = base.CWBinaryBase.unconv_gradientdir(e.get("direction", "None"))
                    for e_grd in e:
                        if e_grd.tag == "EndColor":
                            color2 = getcolor(e_grd, color2)

            elif data.tag == "PCCell":
                f.check_wsnversion("1")

        if data.tag == "BgImage":
            f.write_dword(left)
            f.write_dword(top)
            f.write_dword(width + 50000)
            f.write_dword(height)
            f.write_string(imgpath)
            f.write_bool(mask)
            f.write_string(flag)
            f.write_byte(unknown)

        elif data.tag == "TextCell":
            f.check_version(1.50)
            f.write_dword(left)
            f.write_dword(top)
            f.write_dword(width + 60000)
            f.write_dword(height)

            f.write_bool(mask)
            f.write_string(text, True)
            f.write_string(fontface)
            f.write_dword(fontsize)
            f.write_ubyte(color[0])
            f.write_ubyte(color[1])
            f.write_ubyte(color[2])
            f.write_ubyte(color[3])
            style = 0
            if bold:        style |= 0b00000001
            if italic:      style |= 0b00000010
            if underline:   style |= 0b00000100
            if strike:      style |= 0b00001000
            if btype <> -1: style |= 0b00010000
            if vertical:    style |= 0b00100000
            f.write_byte(style)
            if btype <> -1:
                f.write_byte(btype)
                f.write_ubyte(bcolor[0])
                f.write_ubyte(bcolor[1])
                f.write_ubyte(bcolor[2])
                f.write_ubyte(bcolor[3])
                f.write_dword(bwidth)
            f.write_byte(100) # 不明(100)
            f.write_dword(0) # 不明(0)
            f.write_dword(0) # 不明(0)
            f.write_byte(2 if vertical else 0) # 不明(縦書き時:2,他:0)
            f.write_string(flag)
            f.write_byte(unknown)

        elif data.tag == "ColorCell":
            f.check_version(1.50)
            f.write_byte(blend)
            f.write_byte(gradient)
            f.write_ubyte(color1[2]) # RGBの順序が逆
            f.write_ubyte(color1[1])
            f.write_ubyte(color1[0])
            f.write_ubyte(color1[3])
            if gradient <> 0:
                f.write_ubyte(color2[2]) # RGBの順序が逆
                f.write_ubyte(color2[1])
                f.write_ubyte(color2[0])
                f.write_ubyte(color2[3])
            f.write_string(flag)
            f.write_byte(unknown)

        elif data.tag == "PCCell":
            f.check_wsnversion("1")

def main():
    pass

if __name__ == "__main__":
    main()
