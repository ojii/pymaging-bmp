# -*- coding: utf-8 -*-
# Copyright (c) 2012, Jonas Obrist
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the Jonas Obrist nor the
#      names of its contributors may be used to endorse or promote products
#      derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL JONAS OBRIST BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from collections import namedtuple
from functools import partial
from pymaging.colors import RGB
from pymaging.image import Image
from pymaging.formats import Format
from pymaging.exceptions import FormatNotSupported
import array
import struct
from pymaging.pixelarray import get_pixel_array


PIXEL_SIZES = {
    32: 3,
    24: 3,
    1: 1,
}


class BMPHeader(object):
    def __init__(self, width, height, nplanes, bits_per_pixel, compression_method, bmp_bytesz, hres, vres, ncolors,
                 nimpcolors, offset, palette_start):
        self.width = width
        self.height = height
        self.nplanes = nplanes
        self.bits_per_pixel = bits_per_pixel
        self.compression_method = compression_method
        self.bmp_bytesz = bmp_bytesz
        self.hres = hres
        self.vres = vres
        self.ncolors = ncolors
        self.nimpcolors = nimpcolors
        self.offset = offset
        self.palette_start = palette_start
        self.pixelsize = PIXEL_SIZES[self.bits_per_pixel]
        self.pixelwidth = self.width * self.pixelsize


def BITMAPINFOHEADER(fileobj, offset, palette_start):
    raw_headers = struct.unpack_from('<IihhiiIIii', fileobj.read(36))
    raw_headers += (offset, palette_start)
    headers = BMPHeader(*raw_headers)
    if headers.nplanes != 1:
        raise ValueError("Unexpected nplanes: %r" % headers.nplanes)
    return headers

HEADER_READERS = {
    40: BITMAPINFOHEADER,
    52: BITMAPINFOHEADER,
    56: BITMAPINFOHEADER,
    108: BITMAPINFOHEADER,
    124: BITMAPINFOHEADER,
}


def read_row_32bit(fileobj, headers, pixel_array, row_num):
    row_start = row_num * headers.pixelwidth
    for x in range(headers.width):
        # not sure what the first thing is used for
        _, b, g, r =  struct.unpack('<BBBB', fileobj.read(4))
        start = row_start + (x * headers.pixelsize)
        pixel_array.data[start] = r
        pixel_array.data[start + 1] = g
        pixel_array.data[start + 2] = b

def read_row_24bit(fileobj, headers, pixel_array, row_num):
    row = array.array('B')
    row.fromfile(fileobj, headers.pixelwidth)
    start = row_num * headers.pixelwidth
    end = start + headers.pixelwidth
    pixel_array.data[start:end] = row
    fileobj.read(headers.pixelwidth % 4) # padding

def read_row_1bit(fileobj, headers, pixel_array, row_num):
    padding = 32 - (headers.width % 32)
    row_length = (headers.width + padding) // 8
    start = row_num * headers.pixelwidth
    item = 0
    for b in struct.unpack('%sB' % row_length, fileobj.read(row_length)):
        for _ in range(8):
            a, b = divmod(b, 128)
            pixel_array.data[start + item] = a
            item += 1
            if item >= headers.width:
                return
            b <<= 1


ROW_READERS = {
    32: read_row_32bit,
    24: read_row_24bit,
    1: read_row_1bit,
}


def read_headers(fileobj):
    magic = struct.unpack('<bb', fileobj.read(2))
    if magic != (66, 77):
        raise ValueError("Invalid magic number: %r" % magic)
    struct.unpack('<i', fileobj.read(4))[0] # file length
    fileobj.read(4) # reserved/unused stuff
    offset = struct.unpack('<i', fileobj.read(4))[0]
    pre_header = fileobj.tell()
    headersize = struct.unpack('<i', fileobj.read(4))[0]
    palette_start = pre_header + headersize
    return HEADER_READERS[headersize](fileobj, offset, palette_start)


def read_pixels(fileobj, headers):
    fileobj.seek(headers.palette_start)
    palette = []
    for _ in range(headers.ncolors):
        blue, green, red, _ = struct.unpack('<BBBB', fileobj.read(4))
        palette.append((red, green, blue))
    # set palette to None instead of empty list when there's no palette
    palette = palette or None

    read_row = ROW_READERS[headers.bits_per_pixel]

    fileobj.seek(headers.offset)
    # since bmps are stored upside down, initialize a pixel list
    initial = array.array('B', [0] * headers.width * headers.height * headers.pixelsize)
    pixel_array = get_pixel_array(initial, headers.width, headers.height, headers.pixelsize)
    # iterate BACKWARDS over the line indices so we don't have to reverse
    # later. this is why we intialize pixels above.
    for row_num in range(headers.height - 1, -1, -1):
        read_row(fileobj, headers, pixel_array, row_num)

    return pixel_array, palette


def open_image(fileobj):
    try:
        headers = read_headers(fileobj)
    except:
        fileobj.seek(0)
        return None
    loader = partial(read_pixels, fileobj, headers)
    # TODO: is this really always RGB?
    return Image(RGB, headers.width, headers.height, loader, meta={'source_format': 'BMP'})

def save_image(image, fileobj):
    raise FormatNotSupported('bmp')

BMP = Format(open_image, save_image, ['bmp'])
