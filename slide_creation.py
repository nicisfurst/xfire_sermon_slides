## Imports
from dataclasses import field
from textwrap import fill
from unittest.mock import DEFAULT
from PIL import Image, ImageDraw, ImageFont
from json import load
import pandas as pd
from string import ascii_letters, ascii_lowercase
from math import ceil, floor


# Const
IMG_QUALITY = 100
TEMPLATES_FILE = 'templates.json'
EMPTY_SECTION = 'empty'
TEXT_SECTION = 'text'
TITLE_SECTION = 'title_text'
FONT_DIR = 'fonts'
BG_DIR = 'backgrounds'
OUTLINE_COLOR = '#ff0000'
OUTLINE_WIDTH = 10
DECREMENT_STEP = 10  # pt
MIN_SPACING = 6


################
## SECTIONS ####
################
"""
section
- size 
- pos
- item/block

text block
- text
- - upper
- - char wrap
- font
- color
- align
- anchor
- spacing
- size

image block
- image
- scaling / fill options
- subdivide into multiple imgs
"""

class Section:
    def __init__(self, width: int, height: int, x: int, y: int) -> None:
        """Initializer for the generic section class

        Args:
            width (pixels): Width of the section
            height (pixels): Height of the section
            abs_x (pixels): Absolute x position of the section relative to its slide
            abs_y (pixels): Absolute y position of the section relative to its slide
        """
        self.width:  int = width
        self.height: int = height
        self.x:      int = x
        self.y:      int = y
    
    def draw(self, draw: ImageDraw.ImageDraw):
        pass
    
    def draw_outline(self, draw: ImageDraw.ImageDraw):
        draw.rectangle([
             (self.x, self.y), 
             (self.x + self.width, self.y + self.height)
            ], outline=OUTLINE_COLOR, width=OUTLINE_WIDTH)

    @staticmethod
    def add_from_template(slide, x: int, y: int, 
                          width: int, height: int, section_template: int
                          ) -> None:

        match section_template['type']:
            case 'empty':
                slide.add_section(Section(width, height, x, y))
            
            case 'text':
                # Check how many fields have actually been entered in from form
                n = 0
                for field in section_template['fields']:
                    if not null_field(slide.data, slide.field_suffix, field):
                        n += 1
                assert(n > 0)
                
                new_sections = []
                height = height / n
                for field in section_template['fields']:
                    if null_field(slide.data, slide.field_suffix, field):
                        continue
                    
                    new_sections.append(TextSection(
                        width, height, x, y, slide.data[field + slide.field_suffix], 
                        section_template['size'], section_template['force_upper'], 
                        section_template['spacing'], section_template['font'], 
                        section_template['color'], section_template['align'],
                        section_template['anchor']))
                    y += height
                    
                min_size = new_sections[0].size
                for section in new_sections:
                    if section.size < min_size:
                        min_size = section.size
                
                for section in new_sections:
                    section.adjust_size(min_size)
                    slide.add_section(section)
            
            case 'title_text':
                slide.add_section(TextSection(
                    width, height, x, y, slide.title, 
                    section_template['size'], section_template['force_upper'], 
                    section_template['spacing'], section_template['font'], 
                    section_template['color'], section_template['align'],
                    section_template['anchor']))
            
            case _:
                raise ValueError(f'Unknown slide section type {section_template["type"]}')
        

class TextSection(Section):
    def __init__(
                self, width: int, height: int, x: int, y: int,
                text: str, size: str, force_upper: bool, spacing: int,
                font_name: str, color: str, align: str, anchor: str,
                dynamic_sizing: bool = True
                ) -> None:
        # Call init of Section class
        super().__init__(width, height, x, y)
        
        # Add class properties
        text = str(text)
        self.text = text.upper() if force_upper else text
        self.size = size
        self.spacing = spacing
        self.font_name = f'{FONT_DIR}/{font_name}'
        self.color = color
        self.align = align
        self.anchor = anchor
    
        self.build_font()
        
        # Formatting
        if dynamic_sizing:
            self.format_text()
    
    def build_font(self):
        self.font = ImageFont.truetype(self.font_name, size=self.size)
    
    def format_text(self):
        # TODO: Can be greatly optimised as every slide does not need to re render text for sizing
        n = len(self.text)
        
        finished = False
        
        while not finished:
            # _, _, w, h = self.font.getmask(self.text).getbbox()
            # hi, _ = self.font.getmetrics()
            # sizes = [self.font.getsize(char) for char in ascii_letters]
            # w = sum(char[0] for char in sizes) / len(ascii_lowercase)
            # h = sum(char[1] for char in sizes) / len(ascii_lowercase)
            sizes = self.font.getsize(self.text)
            w = sizes[0] / n
            h = sizes[1]
            chars_per_line = ceil(self.width / w)
            n_lines = ceil(n / chars_per_line)
            # chars_per_line = self.width * n / w
            # n_lines = n / char_per_line

            if (n_lines * h >= self.height):
                self.adjust_size(self.size - DECREMENT_STEP)
            else:
                finished = True
            
        self.text = fill(self.text, chars_per_line)

    def adjust_size(self, size: int):
        self.spacing = max(MIN_SPACING, self.spacing*abs(self.size - size)/self.size) 
        self.size = size
        self.build_font()
    
    def draw(self, draw: ImageDraw.ImageDraw):
        match self.align:
            case 'center':
                x = self.x + self.width / 2
                y = self.y + self.height / 2
                assert(self.anchor == 'mm')
            
            case 'left':
                x = self.x
                y = self.y + self.height / 2
                assert(self.anchor == 'lm')
            
            case _:
                raise ValueError("Invalid section alignment")
        
        draw.text((x, y), self.text, fill=self.color, font=self.font,
                  anchor=self.anchor, spacing=self.spacing, 
                  align=self.align)


################
## SLIDES ######
################
"""
slide
- sections
- background
- size 

text slide
- slide attr
- main text 
- footer text

image slide
- slide attr
- main image
"""

class Slide:
    def __init__(self, width: int, height: int, bg: str | Image.Image,
                 title: str, *args, **kwargs) -> None:
        """Base Slide Class

        Args:
            width (pixels): Width of slide
            height (pixels): Height of slide
            bg_name (str): Name of background file
        """
        self.width  = width
        self.height = height
        self.title  = title
        self.sections: list[Section] = []
        
        if isinstance(bg, Image.Image):
            self.bg = Image
        elif isinstance(bg, str):
            self.bg = Image.open(f'{BG_DIR}/{bg}')
            self.bg = self.bg.resize((width, height), resample=Image.LANCZOS)
        else:
            raise ValueError("bg not a valid type")
    
        self.draw = ImageDraw.Draw(self.bg)
        
        self.data = None
        self.field_suffix = None
        
        self.outline_sections = True if kwargs['outline_sections'] else False
    
    def add_section(self, section, *args, **kwargs):
        if isinstance(section, Section):
            self.sections.append(section)
        elif isinstance(section, type):
            self.sections.append(section())
        else:
            raise ValueError('Section should be an instance of Section or the type of section you wish to create')
    
    def save(self, file_path: str):        
        for section in self.sections:
            section.draw(self.draw)
            
            if self.outline_sections:
                section.draw_outline(self.draw)
            
        self.bg.save(file_path, quality=IMG_QUALITY)
        
    def read_template(self, template: str, data: pd.Series, 
                      field_suffix: str = ''):

        self.data = data
        self.field_suffix = field_suffix
        
        with open(TEMPLATES_FILE, 'r') as f:
            templates = load(f)
            
        y_offset = 0
        
        for section in templates[template]:
            width = self.width * section['width']
            height = self.height * section['height']
            x_offset = (self.width - width) / 2
            
            Section.add_from_template(self, x_offset, y_offset,
                                      width, height, section)
            
            y_offset += height


def null_field(data: dict, field_suffix: str, field: str) -> bool:
    return pd.isnull(data[field + field_suffix])

