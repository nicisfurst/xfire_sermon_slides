from PIL import Image, ImageFont, ImageDraw
from copy import deepcopy
from textwrap import wrap
import pandas as pd
from tqdm import tqdm
from json import load
import os


# Const
SETUP_DATA = 'setup.json'
IMAGE_TYPE = 'image'
TEXT_TYPE = 'text'
IMG_QUALITY = 100
FONT_DIR = 'fonts/'
BG_DIR = 'backgrounds/'
FIRST_SLIDE_N = 1


def main():
    # Get the data
    rm_old_slides()
    data = get_setup_and_fields()
    setup_data = data['setup']
    df = get_slide_data(setup_data['form'], data['meta_fields'])
    
    # Create PIL Stuff
    bg = load_bg(setup_data['bg'], setup_data['width'], setup_data['height'])
    
    # Create Slides
    slides = get_slides(data, df)
    for i, slide in tqdm(enumerate(slides), total=len(slides)):     
        curr = data['templates'][slide]
        if curr['type'] == TEXT_TYPE:
            make_text_slide(curr['settings'],  curr['fields'], df, i, bg, 
                            setup_data, df[data['meta_fields']['title']])
        elif curr['type'] == IMAGE_TYPE:
            raise(NotImplementedError('can\t yet make images'))
            # make_image_slide(curr['settings'],  curr['fields'], df, i, bg)
        else:
            print(f'Can\'t find {curr["type"]} in the template\'s type')
            print(f'Options are {IMAGE_TYPE} and {TEXT_TYPE}')
            print("SKIPPING THIS SLIDE")
    
    # Slides added, now add title slides
    make_text_slide(data['templates'][data['template_fields']['slide_options'][0]]['settings'], 
                    [data['meta_fields']['title']], df, 0, bg, setup_data, ' ', True)
    
    # End
    input('All Done!')
    

def rm_old_slides():
    for old_slide in os.listdir('slides'):
        assert(old_slide.endswith('.png'))
        os.remove(f'slides/{old_slide}')


def get_setup_and_fields() -> dict:
    with open(SETUP_DATA, 'r') as f:
        data = load(f)
    return data


def get_slide_data(form: str, meta_fields: dict) -> pd.DataFrame:
    df_all = pd.read_csv(form)
    
    print("Please Chose an Index (eg 0, 1)")
    print(df_all.loc[:, meta_fields.values()])
    index = input('> ')
    assert(index.isnumeric())
    
    return df_all.loc[int(index)]


def load_bg(bg: str, width: int, height: int) -> Image:
    img = Image.open(f'{BG_DIR}{bg}')
    img = img.resize((width, height), resample=Image.LANCZOS)
    return img


def get_slides(data: dict, df: pd.DataFrame) -> list:
    fields = df.index.to_list()
    slides = []
    
    i = 0
    slide_type_field = data['template_fields']['slide_type']
    curr_field = slide_type_field
    
    while (curr_field in fields):
        if pd.isnull(df[curr_field]):
            break
        
        slides.append(df[curr_field])
        i += 1
        curr_field = f'{slide_type_field}.{i}'
    
    assert(len(slides) > 0)
    assert(type(slides[0]) == str)
    
    return slides


def make_text_slide(settings: dict,  fields: list, df: pd.DataFrame, i: int, 
                    bg: Image, setup: dict, title: str, 
                    is_title: bool = False) -> None:
    # Init / Prepare
    img = deepcopy(bg)
    draw = ImageDraw.Draw(img)
    font = load_font(settings['font'], settings['size'])
    footer_font = load_font(setup['footer_font'], setup['footer_size'])
    text, footer = load_text(fields, df, settings['char_wrap'], 
                             settings['force_upper'], i, 
                             settings['last_field_footer'])
    if footer is None:
        footer = title
    
    # Draw Text and Save
    height = img.height/2
    if settings['align'] == 'center':
        width = img.width/2
    elif settings['align'] == 'left':
        width = img.width/15
    else:
        raise NotImplementedError('your align isn\'t implemented')
        
    draw.text((width, height), text, setup['text_color'], font=font, 
              anchor=settings['anchor'], align=settings['align'], 
              spacing=settings['spacing'])
    draw.text((img.width/2, img.height*setup['footer_height_pos']), footer, setup['text_color'],
              font=footer_font, anchor='mm', align='center')
    img.save(f'slides/{i+(FIRST_SLIDE_N if not is_title else 0)}.png', quality=IMG_QUALITY)


def ith_field(text: str, i: int):
    if i != 0:
        text = f'{text}.{i}'
    return text
    

def load_font(font: str, size: int):
    return ImageFont.truetype(f'{FONT_DIR}{font}', size)


def load_text(fields: list, df: pd.DataFrame, char_wrap: int, 
              force_upper: bool, i: int, last_field_footer: bool):
    # Get Text
    text_list = []
    for field in fields:
        raw_text = df[ith_field(field, i)]
        if pd.isnull(raw_text): continue
        text_list.append('\n'.join(wrap(str(raw_text), width=char_wrap)))

    # Join and Return
    footer = None
    if last_field_footer:
        footer = text_list.pop(-1)
    
    out = '\n'.join(text_list)
    if force_upper: out = out.upper()
    return out, footer


if __name__ == '__main__':
    main()
