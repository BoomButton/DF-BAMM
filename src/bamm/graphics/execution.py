'''
Created on May 21, 2015

@author: Button
'''

from src.bamm.common import config, parsing
from src.bamm.graphics import graphics


def default_run():
    print("Running with default options.")
    default_setup()
    default_gen_new_raws()


def default_setup():
    config.load_run_config()
    parsing._load_ascii_conversions(config.properties[config.ASCII_FILE][1])
    graphics.load_all_templates(config.properties[config.TEMPLATEFILE][1])


def default_gen_new_raws():
    graphics_tags_by_file = \
        graphics.TagNode.walk_rawfiles_into_tagnode_collection(
            config.properties[config.GRAPHICS_SOURCEDIR][1])
    graphics_tags_by_file = \
        graphics.TagNode.walk_rawfiles_into_tagnode_collection(
            config.properties[config.EXTRA_GRAPHICS_SOURCEDIR][1],
            graphics_tags_by_file)
    target_tags_by_file = \
        graphics.TagNode.walk_rawfiles_into_tagnode_collection(
            config.properties[config.TARGETDIR][1])
    tags_to_apply = \
        graphics.BoundNode.bind_graphics_to_targets(graphics_tags_by_file,
                                                    target_tags_by_file)
    graphics.write_modified_raws(tags_to_apply,
                                 config.properties[config.TARGETDIR][1],
                                 config.properties[config.OUTPUTDIR][1])
