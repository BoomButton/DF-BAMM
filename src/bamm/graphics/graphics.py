import os
import shutil
import traceback
from src.bamm.common import config, parsing

template_tree = None

userlog = config.userlog
modderslog = config.modderslog


# TODO overhaul.
def load_all_templates(templatefile):
    """ Loads config information from templatefile.

    * templatefile is a pipe-delimited, one-graphics-tag-per-line config file
    which should not be changed by users unless you REALLY know what you're
    doing.

    This initializes the scaffolding for all future raw parsing, which is
    stored in graphics.template_tree .
    """
    try:
        userlog.info("Loading template configuration...")
        alltemplates = open(templatefile, 'r')
        global template_tree
        if template_tree is None:
            # initialize the template tree
            template_tree = TemplateNode(None)
        for line in alltemplates:
            real_line = line.strip()
            # Starting at the root of the tree with each newline
            curr_node = template_tree
            if len(real_line) > 0:
                tags = real_line.split('|')
                for tag in tags:
                    if tag in curr_node._children.keys():
                        curr_node = curr_node._children[tag]
                    else:
                        curr_node = TemplateNode(curr_node, tag)

                curr_node._is_graphics_tag = True
        alltemplates.close()
        userlog.info("Template configuration loaded.")
    except:
        userlog.error("Exception in loading templates. " +
                      "If you have made changes to " + templatefile +
                      ", please restore it. " +
                      "Otherwise, please contact a BAMM! developer.")
        userlog.error(traceback.format_exc())
        raise


# TODO Maybe replace graphics_to_apply with curr_dict?
def _apply_graphics_to_file(graphics_to_apply, file, sourceroot, targetpath):
    """ Writes merged raws belonging to a single file.

    * graphics_to_apply is a collection of BoundNode trees formatted as { file:
    {topleveltag:BoundNode}}. This is the format returned by
    BoundNode.bind_graphics_tags.
    * file is the name of the file to apply graphics to, without any
    information about its parent directories.
    * sourceroot is the path to the directory containing the source raw version
    of 'file'.
    * targetpath is the path to the output file, with the name of the file
    included.

    For each line in the raw source file, the function searches BoundNode for a
    matching tag for each tag. If the tag is found, its contents are replaced
    in the line with a merged version from the appropriate BoundNode. Then the
    line - modified or unmodified - is written out to the output file.
    """
    userlog.info("Merging graphics into %s ...", file)
    curr_dict = graphics_to_apply[file]
    curr_node = None
    targetfile = open(targetpath, 'wt', encoding='cp437')
    sourcefile = open(os.path.join(sourceroot, file), 'rt', encoding='cp437')
    linecount = 0
    tags_to_reset_addl = []
    for line in sourcefile:
        linecount = linecount + 1
        modified_line = parsing.escape_problematic_literals(line)
        additional = []
        for tag in parsing.tags(line):
            matching_node = None
            if tag in curr_dict.keys():
                matching_node = curr_dict[tag]
            elif curr_node is not None:
                matching_node = curr_node.find_match(tag)
            if matching_node is not None:
                curr_node = matching_node
                matching_node.pop_self()
                if matching_node.is_there_a_difference():
                    merged_tag = matching_node.get_merged()
                    if merged_tag is not None:
                        replacement = matching_node.get_merged()
                        userlog.debug("Replacing %s with %s at line %i.", tag,
                                      replacement, linecount)
                        modified_line = modified_line.replace(tag, replacement)
                    else:
                        userlog.debug("Removing tag %s at line %i.", tag,
                                      linecount)
                        to_remove = "[" + tag + "]"
                        modified_line = modified_line.replace(to_remove, "")
                    # modified_line = modified_line[:-1] + " (BAMM)\n"
                additional.extend(matching_node.pop_addl())
                tags_to_reset_addl.append(matching_node)
            elif curr_node is not None:
                problem_parent = curr_node.find_targetsonly_owner(tag)
                if ((problem_parent is not None and
                     problem_parent._targets_only[tag].has_graphics_info())):
                    modderslog.info("Object missing graphics information in %s : %s",
                                    targetpath, tag)
                    # Targets without matching graphics
                    modified_line = "No tag corresponding to (" + tag + \
                        ") was found in graphics source. -BAMM\n" + modified_line

        targetfile.writelines(modified_line)
        for tag_node in additional:
            linecount = linecount + 1
            userlog.debug("Adding tag %s at line %i.", tag_node._tag,
                          linecount)
            line_to_write = "[" + tag_node._tag + "]\n"
            targetfile.writelines(line_to_write)

    targetfile.flush()
    userlog.info("Finished outputting %s .", file)
    targetfile.close()
    sourcefile.close()
# Resetting the additional tags for another
    for node in tags_to_reset_addl:
        node.reset_addl()


def write_modified_raws(graphics_to_apply, raws_sourcedir, outputdir):
    """Write the full modified raws to the raw output directory.

    graphics_to_apply is a dict of type string:dict{string:BoundNode}. The top-
    level string keys are filenames. Each filename's value is a dict
    representing the top-level, relevant tags in the target raw file of that
    name. The inner key is the full tag (without brackets), and the BoundNode
    is the top node of the tree that that tag begins.

    Unless you have way too much time on your hands, I recommend you generate
    graphics_to_apply using the bind_graphics_to_targets function.

    The actual writing is done in this way: first, the function walks the
    target raw source directory structure, and duplicates it in the raw output
    directory. Then it walks the target raw source files, looking for each
    filename in graphics_to_apply's keyset, or one of the properties
    graphics_overwrite or graphics_ignore.
        * If it finds the filename in graphics_overwrite, it copies the file
        directly from the corresponding place in the graphics source directory.
        * If it finds the filename in graphics_ignore, or doesn't find the
        filename at all, it copies the file directly from the corresponding
        place in the target raw source directory.
        * If it finds the filename in graphics_to_apply's keyset, it opens the
        file in the target raw source directory, creates and opens a
        corresponding file in the raw output directory, and walks through the
        target raw source file a line at a time, constructing the modified
        file.
    """

    properties = config.properties
    userlog.info("Writing modified raws...")
    os.makedirs(outputdir, exist_ok=True)
    for root, dirs, files in os.walk(raws_sourcedir):
        # Create directories so we don't have any issues later on
        for _dir in dirs:
            targetdir = os.path.join(root, _dir)
            targetdir = outputdir + targetdir[len(raws_sourcedir):]
            if not os.path.exists(targetdir):
                userlog.info("Creating output directory %s", _dir)
                os.makedirs(targetdir, exist_ok=True)
        for file in files:
            targetpath = os.path.join(root, file)
            targetpath = outputdir + targetpath[len(raws_sourcedir):]
            if ((parsing.path_compatible(
                    targetpath, properties[config.GRAPHICS_IGNORE_LIST][1:]) or
                 file not in graphics_to_apply.keys())):
                userlog.info("Copying %s from target source...", file)
                targetpath = shutil.copyfile(os.path.join(root, file),
                                             targetpath)
                userlog.info("%s copied.", file)
            # TODO Need to implement graphics overwrites
#             elif parsing.path_compatible(targetpath,
#                                          properties[config.GRAPHICS_OVERWRITE_LIST][1:]
#                                          ):
#                 pass
            else:
                _apply_graphics_to_file(graphics_to_apply, file, root,
                                        targetpath)

    userlog.info("All files written.")


# TODO implement
# TODO docstring (when method is finished)
def find_graphics_overrides(graphics_directory, graphics_overwrites):
    to_return = []
    userlog.info("Locating graphics override files")
    for root, dirs, files in os.walk(graphics_directory):
        for file in files:
            filepath = os.path.join(root, file)
            if parsing.path_compatible(filepath, graphics_overwrites):
                to_return.append(filepath)
    return to_return


class TreeNode():
    """Parent class for the other Node classes.

    Contains default implementations of common Tree functionality.

    Members:
        * self._parent = the parent TreeNode of this TreeNode. Any given
        subclass of TreeNode should only have TreeNodes of its own type as
        _parent.
        * self._tag = The string that this node represents. This should be
        overridden and re-defined by subclasses.
        * self._children = A dict of type string:TreeNode, where the key is the
        child's ._tag property.
    """

    # TODO docstring
    def __init__(self, parent=None):
        self._parent = parent
        self._children = {}
        self._tag = None

    # TODO docstring
    def add_child(self, child_node):
        self._children[child_node._tag] = child_node

    # TODO docstring
    def find_match(self, tag):
        curr_node = self
        matching_node = None
        out_of_parents = False
        while matching_node is None and curr_node is not None:
            matching_node = curr_node.get_child(tag)
            curr_node = curr_node._parent
        return matching_node

    # TODO docstring
    def get_child(self, tag):
        if tag in self._children.keys():
            return self._children[tag]
        else:
            return None


# TODO docstring
class TemplateNode(TreeNode):
    """A TreeNode tailored for holding graphics templates.

    TemplateNodes store the patterns which define what tags are graphics tags,
    and which of their tokens are immutable, identifying, graphical, or
    irrelevant. Each TemplateNode represents the template for a single type of
    graphics tag.

    Members:
    * _tag is the template string. It is a series of tokens separated by
    colons. Each token is one of the following:
    * LITERAL. This is a string, usually in all caps, which must be present in
    this exact form for a tag to match this template. The first token in a
    template is always a literal. Enums (e.g. the PLANT_GROWTH timing values of
    ALL and NONE) may simulated by splitting a template into multiple
    templates, one for each enum, with the enum in question present as a
    literal.
    * VARIABLE. This is a single character, '?' '$' or '&' (quotes not present
    in _tag).
        * '?' indicates that this is a graphics token. When matching a tag to a
        template, this can match any value. When merging occurs, this token's
        value will come from the graphics source.
        * '&' indicates that this is an info token. When matching a tag to a
        template, this can match any value. When merging occurs, this token's
        value will come from the raw source.
        * '$' indicates that this is an identifier token. When matching a tag
        to a template, this can match any value; but for two tags to match each
        other, they must share the same values for all identifier tokens in
        their template.
    * VARIABLE RANGE. This is a variable character, followed by a range in
    parentheses, e.g. ?(0,3). This means that the tag can contain 0-3
    (inclusive) tokens in this position, all of which hold graphical
    information. The second value is optional - if omitted, it means there is
    no upper bound on how many tokens can be in this series.
    For examples, please see graphics_templates.config . The string between
    each pipe ( | ) is a valid TemplateNode._tag .
    * _children is a dict containing the TemplateNodes representing the types
    of tags which are allowed to be children of the type of tag represented by
    this TemplateNode. The keys are the full _tags of the child TemplateNodes.
    * _childref is the same as _children, but indexed by the first token (the
    "value") of the child's _tag, instead of the full _tag. For convenience/
    performance only.
    * _parent is the TemplateNode representing the type of tag that the type of
    tag this TemplateNode represents can be a child of.
    * _is_graphics_tag is a boolean that lets us know if this tag is a graphics
    tag, as opposed to a template included because it can have graphics
    children. This is necessary because some graphics tags are composed of only
    a single literal token.
    """

    # string does not contain the character '|'.
    def __init__(self, parent, string=""):
        """ Initializes a TemplateNode

        Parameters:
        * parent is the parent TemplateNode of this node, or None. If it is
        None, this TemplateNode will replace the current global template_tree.
        * string is the template-formatted string which will be this
        TemplateNode's _tag.

        After creating itself, if the parent isn't None, it adds itself to its
        parent.
        """
        TreeNode.__init__(self, parent)
        self._is_graphics_tag = False
        self._childref = {}
        self._tag = None
        global template_tree
        if parent is None:
            self._parent = None
            template_tree = self
        else:
            if template_tree is None:
                self._parent = TemplateNode(None, "")
            else:
                self._parent = parent

            self._tag = string

            parent.add_child(self)

    def is_standalone_tag(self):
        """ Returns True if this is a tag without any non-graphical information."""
        return ('$' not in self._tag
                ) and '&' not in self._tag and self._is_graphics_tag

    # TODO docstring
    def add_child(self, node):
        if node._tag in self._children.keys():
            return self._children[node._tag]
        else:
            self._children[node._tag] = node
            first_token = node._tag.split(':')[0]
            if first_token not in self._childref.keys():
                self._childref[first_token] = []
            self._childref[first_token].append(node)
            return node

    # TODO docstring
    def get_child(self, tag):
        if tag in self._children.keys():
            return self._children[tag]
        else:
            return_possibilities = []
            first_token = tag.split(':')[0]
            if first_token in self._childref:
                for child in self._childref[first_token]:
                    return_node = child.get_template_match(tag)
                    if return_node is not None:
                        return_possibilities.append((child, return_node))
                if len(return_possibilities) == 1:
                    return return_possibilities[0][0]
                elif len(return_possibilities) == 0:
                    return None
                else:
                    # TODO error handling
                    userlog.debug("Found more than one matching child. \
                                  Matching children are:")
                    for poss in return_possibilities:
                        userlog.debug(poss[1])
                    possible_tags = [a[1] for a in return_possibilities]
                    winner = TemplateNode._get_best_match(possible_tags)
                    return return_possibilities[possible_tags.index(winner)][0]
            else:
                return None

    # This tells if a single tag matches a single tag; that is, it assumes
    # we've got one element of the |-separated list
    # TODO docstring
    def get_template_match(self, tag_to_compare):
        if self._tag is None:
            return None
        template_token_bag = []
        template_token_bag.append(self._tag.split(':'))
        candidate_tokens = tag_to_compare.split(':')

        ii = 0
        while (len(template_token_bag) > 0 and
               (ii < len(candidate_tokens) or
                ii < len(template_token_bag[0]))):
            good_to_go = False
            for var in template_token_bag:
                if ii < len(candidate_tokens) and ii >= len(var):
                    template_token_bag.remove(var)
                elif ii >= len(var) and len(var) == len(candidate_tokens):
                    good_to_go = True
                elif (ii >= len(candidate_tokens) and
                      (ii >= len(var) or
                       (ii < len(var) and '(0,' not in var[ii]))):
                    template_token_bag.remove(var)
                elif ('&' == var[ii] or '?' == var[ii] or '$' == var[ii] or
                      (ii < len(candidate_tokens) and
                       var[ii] == candidate_tokens[ii])):
                    # This case is an auto-pass
                    good_to_go = True
                else:
                    if '&' in var[ii] or '?' in var[ii] or '$' in var[ii]:
                        varii_type = var[ii][0]
                        varii_range = var[ii][2:var[ii].index(')')].split(',')
                        # If len(varii_range) == 1 then we have a range of
                        # format (x,), indicating any number of :'s
                        if len(varii_range[1]) == 0:
                            varii_range[1] = len(candidate_tokens)-len(var) + 1
                        # For every possible length (the +1 is because range is
                        # exclusive-end and my notation is inclusive-end)
                        for jj in range(int(varii_range[0]),
                                        int(varii_range[1])+1):
                            # Make a copy of var
                            new_var = var[:]
                            # Remove the range item
                            del new_var[ii]
                            # Replace it with (one of the possible lengths)
                            # times the multiplied symbol
                            # If jj is 0 the range item is just removed
                            for kk in range(0, jj):
                                new_var.insert(ii, varii_type)
                            # Place the new variant in the token bag for
                            # evaluation
                            template_token_bag.append(new_var)
                    # No counting, there is a new template_token_bag[ii]
                    template_token_bag.remove(var)
            if good_to_go:
                ii += 1
        for tag in template_token_bag:
            if len(tag) != len(candidate_tokens):
                template_token_bag.remove(tag)  # This isn't working properly?

        if len(template_token_bag) == 0:
            return None
        elif len(template_token_bag) == 1:
            return template_token_bag[0]
        else:
            # TODO error handling
            highest_priority = TemplateNode._get_best_match(template_token_bag)
            userlog.debug("More than one template matched.\nTag: %s Matches:",
                          tag_to_compare)
            for template in template_token_bag:
                userlog.debug("\t%s", template)
            userlog.debug("The highest-priority match is %s", highest_priority)
            # Technically this does in fact have a matching template
            return highest_priority

    # TODO docstring
    @staticmethod
    def _get_best_match(template_tokens_bag):
        if not template_tokens_bag:        # empty bag returns false
            return None
        elif len(template_tokens_bag) == 1:
            return template_tokens_bag[0]
        else:
            best_currently = template_tokens_bag[0]
            best_tokens = 0
            for tag in template_tokens_bag:
                challenger_tokens = 0
                for token in tag:
                    if token != '?' and token != '&' and token != '$':
                        challenger_tokens = challenger_tokens + 1
                if challenger_tokens > best_tokens:
                    best_currently = tag
                    best_tokens = challenger_tokens
            return best_currently

    # TODO docstring
    def how_many_generations(self):
        temp_node = self
        count = -1
        global template_tree
        while temp_node != template_tree:
            temp_node = temp_node._parent
            count = count + 1
        return count


# TODO docstring
class TagNode(TreeNode):

    # TODO docstring
    def __init__(self, filename, template, tag, parent=None):
        TreeNode.__init__(self, parent)
        self._tag = tag
        self._filename = filename
        self._template = template
        self._children = {}
        self._pat_children = {}
        self._pattern = None
        self._pattern = self.get_pattern()

        if parent is not None:
            parent.add_child(self)

    # TODO docstring
    def add_child(self, child_tag_node):
        self._children[child_tag_node._tag] = child_tag_node
        self._pat_children[child_tag_node.get_pattern()] = child_tag_node

    # TODO docstring
    def apply_graphics(self, graphics_node):
        if graphics_node is None:
            return None
        tags = self._tag.split(':')
        graphics = graphics_node._tag.split(':')
        tag_template = self._template.get_template_match(self._tag)
        merged = []
        graphics_template = self._template.get_template_match(graphics_node._tag)

        for ii in range(0, len(tag_template)):
            if tag_template[ii] != graphics_template[ii]:
                userlog.error("Graphics cannot be applied from %s onto %s \
                              because their templates do not match.",
                              graphics_node._tag, self._tag)
            elif tag_template[ii] != '&' and tag_template[ii] != '?':
                if tags[ii] != graphics[ii]:
                    userlog.error("Tags are not compatible because token %i \
                                  does not match. Target: %s Graphics: %s",
                                  ii, tags[ii], graphics[ii])
                else:
                    merged.append(tags[ii])
            elif tag_template[ii] == '&':
                merged.append(tags[ii])
            elif tag_template[ii] == '?':
                merged.append(graphics[ii])
            else:
                userlog.error("This block should never be reached. \
                              Big problem in TagNode.apply_graphics.")

        return ":".join(merged)

    # TODO docstring
    def get_pattern(self):
        if self._pattern is None:
            to_return = self._tag.split(':')
            tag_tokens = self._tag.split(':')
            template_possibilities = self._template.get_template_match(self._tag)
            for ii in range(0, len(tag_tokens)):
                if template_possibilities[ii] in [tag_tokens[ii], '$']:
                    to_return[ii] = tag_tokens[ii]
                elif template_possibilities[ii] in ['?', '&']:
                    to_return[ii] = template_possibilities[ii]
                else:
                    userlog.error("Tag does not match its own template!! \
                                  Tag: %s ; Template: %s",
                                  self._tag, self._template._tag)
            self._pattern = ":".join(to_return)
        return self._pattern

    # TODO docstring
    def aligns_with(self, other_tag):
        return (self._template == other_tag._template
                ) and self.get_pattern() == other_tag.get_pattern()

    # TODO docstring
    def is_standalone_tag(self):
        return self._template.is_standalone_tag()

    # TODO docstring
    def is_graphics_tag(self):
        return self._template._is_graphics_tag

    # TODO docstring
    def has_graphics_info(self):
        to_return = self.is_graphics_tag()
        for child in self._children.keys():
            to_return |= self._children[child].has_graphics_info()
            if to_return:
                break
        return to_return

    @staticmethod
    def walk_rawfiles_into_tagnode_collection(directory, node_collection=None):
        """Load the graphics-relevant content of raw files into memory.

        * directory is a directory containing the raw files you want to load
        into memory. Files with duplicate names will be treated as the same
        file, even if they're in different sub-folders.
        * node_collection is an optional parameter, to let you add additional
        raw files to the same node_collection. It is formatted the same as the
        return dict.

        The function returns a dictionary of string:dict{string:TagNode}. The
        outer key is a filename which contains some graphics-relevant content.
        The inner key is the tag corresponding with a top-level TagNode in that
        file, and maps to that TagNode.

        This format is the expected input format of both parameters of
        bind_graphics_to_targets(graphics_nodes, target_nodes).
        """
        if node_collection is None:
            node_collection = {}

        try:
            for root, dirs, files in os.walk(directory):
                for rawfile in files:
                    # Only look at .txt files
                    if '.txt' not in rawfile:
                        userlog.info("Skipping file %s...", rawfile)
                        continue
                    userlog.info("Loading graphics tags from %s...", rawfile)
                    global template_tree
                    # curr_template_node keeps track of what format of tag
                    # we've most recently seen, and thus what's valid next
                    curr_template_node = template_tree
                    # curr_real_node keeps track of the tag we stored that
                    # corresponds to the most local instance of
                    # curr_template_node.
                    curr_real_node = None
                    tarpath = os.path.join(root, rawfile)
                    openfile = open(tarpath, encoding='cp437')
                    for line in openfile:
                        for tag in parsing.tags(line):
                            matching_node = curr_template_node.find_match(tag)
                            if matching_node is not None:
                                curr_template_node = matching_node
                                if ((curr_real_node is None or
                                     matching_node._tag in template_tree._children)):
                                    curr_real_node = TagNode(rawfile,
                                                             matching_node,
                                                             tag)
                                else:
                                    while (curr_real_node is not None and
                                           matching_node._tag not in
                                           curr_real_node._template._children):
                                        curr_real_node = curr_real_node._parent
                                    curr_real_node = TagNode(rawfile,
                                                             matching_node,
                                                             tag,
                                                             curr_real_node)
                                if rawfile not in node_collection:
                                    node_collection[rawfile] = {}
                                if curr_real_node._parent is None:
                                    node_collection[rawfile][tag] = curr_real_node

                    openfile.close()
                    userlog.info("Finished processing %s .", rawfile)
        except:
            userlog.error("Exception in loading raws.")
            userlog.error(traceback.format_exc())
        else:
            return node_collection


# TODO docstring
class BoundNode(TreeNode):
    def __init__(self, target_node, graphics_node, parent=None):
        TreeNode.__init__(self, parent)
        self._tag = target_node._tag
        self._popped_children = {}
        self._additional = []
        self._targets_only = {}
        self._are_addl_popped = False
        self._target_node = target_node
        self._graphics_node = graphics_node
        if parent is not None:
            parent.add_child(self)
        else:
            self.create_child_nodes()

    # TODO docstring
    def add_child(self, child_node):
        self._children[child_node._target_node._tag] = child_node
        self._popped_children[child_node._target_node._tag] = False

    # TODO docstring
    def is_graphics_tag(self):
        if self._target_node.is_graphics_tag() != self._graphics_node.is_graphics_tag():
            userlog.error("Problem in BoundNode.is_graphics_tag for BoundNode %s",
                          self._tag)
        return self._target_node.is_graphics_tag()

    # TODO docstring
    def create_child_nodes(self):
        # Children with pattern keys in both target & graphics
        for shared_key in set(self._target_node._pat_children.keys()
                              ).intersection(set(self._graphics_node._pat_children.keys())):
            new_node = BoundNode(self._target_node._pat_children[shared_key],
                                 self._graphics_node._pat_children[shared_key],
                                 self)
            self.add_child(new_node)
            new_node.create_child_nodes()
        # Children with pattern keys in target but not in graphics
        for target_key in set(self._target_node._pat_children.keys()
                              ) - set(self._graphics_node._pat_children.keys()):
            target_in_question = self._target_node._pat_children[target_key]
            if target_in_question.is_standalone_tag():
                self.add_child(BoundNode(target_in_question, None, self))
            else:
                self._targets_only[target_in_question._tag] = target_in_question
        # Children with pattern keys in graphics but not in target
        for graphics_key in set(self._graphics_node._pat_children.keys()
                                ) - set(self._target_node._pat_children.keys()):
            graphics_in_question = self._graphics_node._pat_children[graphics_key]
            if graphics_in_question.is_standalone_tag():
                self._additional.append(graphics_in_question)
        # End

    # TODO docstring
    def are_all_children_popped(self):
        to_return = True
        for child in self._popped_children.keys():
            to_return &= self._popped_children[child]
        return to_return

    # TODO docstring
    def pop_addl(self):
        to_return = []
        # If this hasn't had its additionals popped and is ready to pop
        if (not self._are_addl_popped):
            self._are_addl_popped = True
            to_return.extend(self._additional)
        if self._parent is not None:
            to_return.extend(self._parent.pop_addl())
        return to_return

    # TODO docstring
    def reset_addl(self):
        self._are_addl_popped = False
        for child in self._children.keys():
            self._children[child].reset_addl()

    # TODO docstring
    def get_merged(self):
        return self._target_node.apply_graphics(self._graphics_node)

    # TODO docstring
    def pop_child(self, target_tag):
        if target_tag not in self._children.keys():
            return self
        else:
            if self._popped_children[target_tag]:
                userlog.warning("Popping tag that has already been popped: %s \
                                child of %s", target_tag, self._tag)

            return self._children[target_tag]

    # TODO docstring
    def pop_self(self):
        if self._parent is not None:
            also_self = self._parent.pop_child(self._tag)
            if also_self != self:
                userlog.error("Big problem: Bound Node with _tag %s is not its \
                              parent's ._children[%s]", self._tag, self._tag)
        return self

    # TODO docstring
    def is_there_a_difference(self):
        if self._graphics_node is None:
            return True
        elif self._target_node._tag == self._graphics_node._tag:
            return False
        else:
            return True

    # TODO docstring
    def find_targetsonly_owner(self, target_tag):
        if target_tag in self._targets_only:
            return self
        elif self._parent is not None:
            return self._parent.find_targetsonly_owner(target_tag)
        else:
            return None

    @staticmethod
    def bind_graphics_to_targets(graphics_nodes, targets_nodes):
        """Associate two collections of TagNodes with each other,
        in preparation for merging.

        * graphics_nodes and targets_nodes are dicts of type
        string:dict{string:TagNode}, where the outer key is a file name, the
        inner keys are tags associated with top-level TagNodes, and the
        TagNodes are of course those same top-level TagNodes. These
        string:string:TagNodes are expected to be produced by
        walk_rawfiles_into_tagnode_collection.

        The function returns a similarly-formatted dict of BoundNodes, in the
        format string:dict{string:BoundNode}, where the outer key is a file
        name, the inner key is the tag associated with the target_nodes of top
        level BoundNodes, and the BoundNodes are, as usual, those BoundNodes.

        The BoundNodes in the return dict are generated from the two arguments,
        by matching up TagNodes from graphics_nodes and targets_nodes based on
        their filenames, templates, and parents.

        If a TagNode in graphics_nodes has no corresponding TagNode in
        targets_nodes, it is evaluated for standalone status. If it is a
        standalone tag, it is added to _additional; otherwise it is dropped.
        If a TagNode in target_nodes has no corresponding TagNode in
        graphics_nodes, it is also evaluated for standalone status. If it's
        a standalone tag it is paired with None. If not, it is then checked
        to see if it has any graphical descendants. If it does, it's added
        to _targets_only and will be logged to the modders' log (default
        location missing.log ). If not, it is dropped.
        """
        userlog.info("Binding graphics source tags to target tags...")
        to_return = {}
        for filename in targets_nodes.keys():
            # Files which both share, both have found graphics in, and haven't
            # been put in the return dict yet.
            if ((filename in graphics_nodes.keys() and
                 filename not in to_return.keys())):
                userlog.info("Binding tags for %s ...", filename)
                to_return[filename] = {}
                for top_level_tag in targets_nodes[filename].keys():
                    # Top level tags which both share, both have found graphics
                    # in, and haven't been put in the return dict yet.
                    if ((top_level_tag in graphics_nodes[filename] and
                         top_level_tag not in to_return[filename].keys())):
                        # Create new BoundNode tree and put it in the return
                        # dict.
                        to_return[filename][top_level_tag] = \
                            BoundNode(targets_nodes[filename][top_level_tag],
                                      graphics_nodes[filename][top_level_tag])
                userlog.info("%s tags bound.", filename)
        userlog.info("Tag binding complete.")
        return to_return
