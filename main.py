# Imports
from copy import deepcopy
from tqdm import tqdm
import pandas as pd
import os
from json import load
from sys import argv

import slide_creation


# Const
SETUP_DATA = 'setup.json'
FONT_DIR = 'fonts/'
BG_DIR = 'backgrounds/'
SLIDE_DIR = 'slides/'
DEBUG = True
DEBUG_I = False


def main():
    rm_old_slides()
    setup = get_setup()
    data = get_slide_data(setup['form'], setup['meta_fields'])
    slides = get_slides(setup, data)
    make_slides(slides)


def rm_old_slides():
    for old_slide in os.listdir(SLIDE_DIR):
        if old_slide.endswith('.png'):
            os.remove(f'{SLIDE_DIR}/{old_slide}')


def get_setup() -> dict:
    with open(SETUP_DATA, 'r') as f:
        data = load(f)
    return data


def get_slide_data(form: str, meta_fields: dict) -> pd.DataFrame:
    df_all = pd.read_csv(form)
    
    if not DEBUG_I:
        print("Please Chose an Index (eg 0, 1)")
        print(df_all.loc[:, [meta_fields['name'], meta_fields['title']]])
        index = input('> ')
        assert(index.isnumeric())
    else:
        index = DEBUG_I
    
    return df_all.loc[int(index)]


def get_slides(setup: dict, data: pd.DataFrame) -> list:
    fields = data.index.to_list()
    slide_types = []
    
    i = 0
    slide_type_field = setup['meta_fields']['slide_type']
    curr_field = slide_type_field
    
    while (curr_field in fields):
        if pd.isnull(data[curr_field]):
            break
        
        slide_types.append(data[curr_field])
        i += 1
        curr_field = f'{slide_type_field}.{i}'
    
    assert(len(slide_types) > 0)
    assert(type(slide_types[0]) == str)
    
    slides = []
    sermon_title = data[setup['meta_fields']['title']]
    for i, slide_type in enumerate(slide_types):
        new_slide = slide_creation.Slide(setup['width'], setup['height'], 
                                 setup['bg'], sermon_title, outline_sections=DEBUG)
        new_slide.read_template(slide_type, data, f'.{i}' if i != 0 else '')
        slides.append(new_slide)
    
    return slides


def make_slides(slides: list[slide_creation.Slide]):
    for i, slide in tqdm(enumerate(slides), total=len(slides)):
        slide.save(f'{SLIDE_DIR}/{i}.png')


if __name__ == '__main__':
    main()
