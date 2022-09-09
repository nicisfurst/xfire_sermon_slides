# SERMON SLIDE GENERATOR
# Written by Nic Furst
#
# Tool to automatically generate sermon slides
#
# Usage:
# A google form is used, and its csv is downloaded into the root directory.
# The program then reads the csv and the user chooses which input they want to
# use to generate sermon slides. The program will then interpret the fields
# via the templates.json file. The slides will be generated and output into 
# the slides directory


# Imports
from tqdm import tqdm
import pandas as pd
from json import load
import os
import argparse
import logging
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
from shutil import rmtree

# Local Imports
from constants import *
import slide_creation

# Other Constants
TITLE_SLIDE = True
TITLE_TEMPLATE = 'Title'

# Initialise Logging
logging.basicConfig(level=INFO, 
                    format=LOGGING_FORMATTER, 
                    filename='logs', 
                    filemode='w')
logger = logging.getLogger(__name__)


###################
# Main Operations #
###################

# Main Function
def main():
    # Get Setup Data
    setup = get_setup()
    df    = get_form_data(setup['form'])
    
    # Main Loop
    while True:
        cleanup_slides()
        sermon_data = get_sermon_data(df, setup['meta_fields'])
        if sermon_data is None:
            logger.log(DEBUG, 'sermon_data is None, breaking main loop')
            break
        
        add_slide_tmp()
        slides = get_slides(setup, sermon_data)
        make_slides(setup, sermon_data, slides, title_slide=TITLE_SLIDE)
        remove_slide_tmp()
        print('Done!')
        
        if not args.multi:
            break
    
    if not isinstance(args.index, int):
        input('Press Enter to Exit!')


# Gets the pandas series with the data for a given sermon
def get_sermon_data(df: pd.DataFrame, meta_fields: dict) -> pd.Series:
    # Series specified in the cmd arguments
    if isinstance(args.index, int):
        index = args.index
        
    # Ask user for sermon
    else:
        print("Please Chose an Index (eg 0, 1) OR Press Enter to Exit.")
        print(df.loc[:, [meta_fields['name'], meta_fields['title']]])
        index = input('> ')
        if index == '':
            return None
        assert(index.isnumeric())
        
    return df.loc[int(index)]


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
        new_slide = slide_creation.Slide(setup['width'], 
                                         setup['height'], 
                                         setup['bg'], 
                                         sermon_title, 
                                         outline_sections=args.outlines)
        new_slide.read_template(slide_type, data, f'.{i}' if i != 0 else '')
        slides.append(new_slide)
    
    return slides

def make_slides(setup: dict, data: pd.DataFrame,
                slides: list[slide_creation.Slide], title_slide: bool = True):
    starting_i = 0
    
    if title_slide:
        logger.log(DEBUG, 'Making Title Slide')
        starting_i += 1
        title = data[setup['meta_fields']['title']]
        title_slide = slide_creation.Slide(setup['width'], 
                                           setup['height'], 
                                           setup['bg'], 
                                           title)
        title_slide.read_template(TITLE_TEMPLATE, data)
        title_slide.save(f'{SLIDE_DIR}/{0}.png', starting_i, outlines=args.outlines)
    
    for i, slide in tqdm(enumerate(slides), total=len(slides)):
        i = i + starting_i
        logger.log(DEBUG, f'Making Slide {i=} {type(slide)=}')
        slide.save(f'{SLIDE_DIR}/{i}.png', i, outlines=args.outlines)


####################
# Helper Functions #
####################

# Removes the existing slides in the slides directory
def cleanup_slides():
    for old_slide in os.listdir(SLIDE_DIR):
        if old_slide.endswith('.png'):
            os.remove(f'{SLIDE_DIR}/{old_slide}')

# Gets setup json dict. Returns 
def get_setup() -> dict:
    with open(SETUP_DATA, 'r') as f:
        data = load(f)
    return data

# Gets the form data as a Pandas DataFrame
def get_form_data(form: str) -> pd.DataFrame:
    df = pd.read_csv(form)
    return df.reindex(index=df.index[::-1]).reset_index()

# Adds tmp folder
def add_slide_tmp():
    if TMP_DIR in os.listdir():
        logger.log(INFO, 'TMP_DIR already exists, skip mkdir.')
        return 
    logger.log(DEBUG, 'Creating TMP dir.')
    os.mkdir(TMP_DIR)

# Removes tmp folder
def remove_slide_tmp():
    if TMP_DIR not in os.listdir():
        logger.log(INFO, 'TMP dir doesn\'t exist when trying to remove it.')
        return
    logger.log(DEBUG, 'Removing TMP dir.')
    rmtree(TMP_DIR)


####################
# Start Of Program #
####################

if __name__ == '__main__':
    # Enable command line functionality
    parser = argparse.ArgumentParser(description='Automatically Generate Sermon Slides')
    parser.add_argument('-i', '--index', type=int,
                        help='Index of the sermon series you want to create. Use 0 for most recent.')
    parser.add_argument('-o', '--outlines', action='store_true',
                        help='Adds rectangle outlines around your slide\'s sections.')
    parser.add_argument('-m', '--multi', action='store_true',
                        help='Allows you to run the program multiple time without exiting.')
    global args    
    args = parser.parse_args()
    
    # Set up the program and make sure everything is ready
    if not os.path.exists(BG_DIR):
        logger.log(DEBUG, f'Directory: {BG_DIR} doesn\'t exist, creating')
        os.mkdir(BG_DIR)
    if not os.path.exists(FONT_DIR):
        logger.log(DEBUG, f'Directory: {FONT_DIR} doesn\'t exist, creating')
        os.mkdir(FONT_DIR)
    if not os.path.exists(SLIDE_DIR):
        logger.log(DEBUG, f'Directory: {SLIDE_DIR} doesn\'t exist, creating')
        os.mkdir(SLIDE_DIR)

    # Run the Main Program
    main()
