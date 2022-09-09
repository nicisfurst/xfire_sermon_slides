## Imports
import pandas as pd
import gdown
import logging
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
from textwrap import fill
from PIL import Image, ImageDraw, ImageFont
from json import load
from math import ceil
from constants import *

# Other Const
IMG_QUALITY = 100
EMPTY_SECTION = 'empty'
TEXT_SECTION = 'text'
TITLE_SECTION = 'title_text'
OUTLINE_COLOR = '#ff0000'
OUTLINE_WIDTH = 10
DECREMENT_STEP = 10  # pt
MIN_SPACING = 6

# Logging
logger = logging.getLogger(__name__)


################
## SECTIONS ####
################

class Section:
    def __init__(self, width: int, height: int, x: int, y: int) -> None:
        """Initializer for the generic section class

        Args:
            width (pixels): Width of the section
            height (pixels): Height of the section
            x (pixels): Absolute x position of the section relative to its slide
            y (pixels): Absolute y position of the section relative to its slide
        """
        self.width:  int = width
        self.height: int = height
        self.x:      int = x
        self.y:      int = y
    
    def draw(self, bg: Image.Image, draw: ImageDraw.ImageDraw, n: int):
        pass
    
    def draw_outline(self, draw: ImageDraw.ImageDraw):
        draw.rectangle([(self.x, self.y), 
                        (self.x + self.width, self.y + self.height)], 
                       outline=OUTLINE_COLOR, width=OUTLINE_WIDTH)

    @staticmethod
    def add_from_template(slide, x: int, y: int, 
                          width: int, height: int, section_template: int
                          ) -> None:
        # TODO: Refactor params to be consistent with elsewhere in the code
        match section_template['type']:
            case 'empty':
                slide.add_section(Section(width, height, x, y))
            
            case 'text':
                # Check how many fields have actually been entered in from form
                n = 0
                for field in section_template['fields']:
                    if slide.field_exists(field):
                        n += 1
                assert(n > 0)
                
                new_sections = []
                height = height / n
                for field in section_template['fields']:
                    if not slide.field_exists(field):
                        continue
                    
                    new_sections.append(TextSection(
                        width, height, x, y, slide.get_data(field), 
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
            
            case 'image':
                slide.add_section(ImageSection(
                    width, height, x, y, 
                    slide.get_data(section_template['fields'][0]),
                    section_template['crop']))
            
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
            sizes = self.font.getsize(self.text)
            w = sizes[0] / n
            h = sizes[1]
            chars_per_line = ceil(self.width / w)
            n_lines = ceil(n / chars_per_line)

            if (n_lines * h >= self.height):
                self.adjust_size(self.size - DECREMENT_STEP)
            else:
                finished = True
            
        self.text = fill(self.text, chars_per_line)

    def adjust_size(self, size: int):
        self.spacing = max(MIN_SPACING, self.spacing*abs(self.size - size)/self.size) 
        self.size = size
        self.build_font()
    
    def draw(self, bg: Image.Image, draw: ImageDraw.ImageDraw, *args, **kwargs):
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


class ImageSection(Section):
    def __init__(self, width: int, height: int, x: int, y: int,
                 url: str, crop: bool) -> None:
        # Call init of super class
        super().__init__(width, height, x, y)
        
        # Add additional properties
        self.url = url
        self.crop = crop
        self.image = None
        
        # oth
        if crop:
            # TOOD: Add logger 
            pass
        
    def add_image(self, n: int):
        # Download the image
        fpath = f'{TMP_DIR}/{n}.png'
        gdown.download(self.url, fpath, fuzzy=True, quiet=True)   
        
        # Load the image
        self.image = Image.open(fpath)
    
    def draw(self, bg: Image.Image, draw: ImageDraw.ImageDraw, n, *args, **kwargs):
        # Get and Resize the image
        self.add_image(n)
        self.image.thumbnail((self.width, self.height), Image.LANCZOS)
        img_x = (self.width - self.image.width) // 2 + self.x
        bg.paste(self.image, (img_x, self.y))
        
        
################
# LOWER THIRDS #
################

class LowerThirds():
    def __init__(self, slide, section_template: dict, all_lt_pos: dict) -> None:
        # Stuff
        self.slide = slide
        self.n_sections = len(section_template['fields'])
        self.sections = []
        lt_pos = all_lt_pos[str(self.n_sections)]
        
        match self.n_sections:
            case 1:
                bg_file = LT1_FILE
            case 2:
                bg_file = LT2_FILE
            case _:
                raise ValueError('Can only have up to two fields for lower thirds.')
            
        self.bg = Image.open(f'{THEME_DIR}/{slide.theme}/{bg_file}')
        self.draw = ImageDraw.Draw(self.bg)
        
        # BG Image
        for i, field in enumerate(section_template['fields']):
            ipos = lt_pos[i]
            self.sections.append(TextSection(ipos['width'], ipos['height'],
                                             ipos['x'], ipos['y'], 
                                             slide.get_data(field), 
                                             ipos['size'], ipos['force_upper'], 
                                             ipos['spacing'], ipos['font'],
                                             ipos['color'], ipos['align'],
                                             ipos['anchor']))
    
    def save(self, file_path: str, n: int, outlines: bool = False):        
        for section in self.sections:
            section.draw(self.bg, self.draw, n)
            
            if outlines:
                section.draw_outline(self.draw)
            
        self.bg.save(file_path, quality=IMG_QUALITY)


################
## SLIDES ######
################

class Slide:
    def __init__(self, width: int, height: int, theme: str,
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
        self.lower_thirds = None
        self.theme = theme
        
        # if isinstance(bg, Image.Image):
        #     self.bg = Image
        if isinstance(theme, str):
            self.bg = Image.open(f'{THEME_DIR}/{theme}/{BG_FILE}')
            self.bg = self.bg.resize((width, height), resample=Image.LANCZOS)
        else:
            raise ValueError("bg not a valid type")
    
        self.draw = ImageDraw.Draw(self.bg)
        
        self.data = None
        self.field_suffix = None
        
        self.outline_sections = kwargs.get('outline_sections', False)
    
    def get_data(self, field: str):
        return self.data[field + self.field_suffix]
    
    def field_exists(self, field: str):
        return not pd.isnull(self.get_data(field))
    
    def add_section(self, section, *args, **kwargs):
        if isinstance(section, Section):
            self.sections.append(section)
        elif isinstance(section, type):
            self.sections.append(section())
        else:
            raise ValueError('Section should be an instance of Section or the type of section you wish to create')
    
    def save(self, file_path: str, n: int, outlines: bool = False):        
        for section in self.sections:
            section.draw(self.bg, self.draw, n)
            
            if outlines:
                section.draw_outline(self.draw)
            
        self.bg.save(file_path, quality=IMG_QUALITY)
        
        if self.lower_thirds != None:
            a = file_path.split('.')
            a[-2] += '_lt'
            file_path = '.'.join(a)
            self.lower_thirds.save(f'{file_path}', n, outlines)
        
    def read_template(self, template: str, setup: dict, data: pd.Series, 
                      field_suffix: str = ''):

        self.data = data
        self.field_suffix = field_suffix
        
        with open(TEMPLATES_FILE, 'r') as f:
            templates = load(f)
            
        y_offset = 0
        
        for section in templates[template]:
            if section['type'] == 'lt':
                self.lower_thirds = LowerThirds(self, section, setup['lt_pos'])
            
            else:
                width = self.width * section['width']
                height = self.height * section['height']
                x_offset = (self.width - width) / 2
                
                Section.add_from_template(self, int(x_offset), int(y_offset),
                                        int(width), int(height), section)
                
                y_offset += height
