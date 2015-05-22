import os
import shutil
from src.bamm.common import config, parsing

template_tree = None

def load_all_templates(templatefile):
    verbose = config.properties[config.DEBUG][1]
    if verbose:
        print("Loading template configuration...")
    alltemplates = open(templatefile,'r')
    global template_tree
    if template_tree is None:
        # initialize the template tree
        template_tree = TemplateNode(None)
    for line in alltemplates:
        real_line = line.strip()
        # Starting at the root of the tree with each newline
        curr_node = template_tree
        if len(real_line) > 0:
            # TODO continue
            tags = real_line.split('|')
            for tag in tags:
                if tag in curr_node._children.keys():
                    curr_node = curr_node._children[tag]
                else:
                    curr_node = TemplateNode(curr_node,tag)
                    
            curr_node._is_graphics_tag = True
    alltemplates.close()
    if verbose:
        print("Template configuration loaded.")

def write_modified_raws(graphics_to_apply, raws_sourcedir, outputdir):
    """Write the full modified raws to the raw output directory.
    
    graphics_to_apply is a dict of type string:dict{string:BoundNode}. The top-level string keys are filenames. Each filename's value is a dict representing the top-level, relevant tags in the target raw file of that name. The inner key is the full tag (without brackets), and the BoundNode is the top node of the tree that that tag begins.
    
    Unless you have way too much time on your hands, I recommend you generate graphics_to_apply using the bind_graphics_to_targets function.
    
    The actual writing is done in this way: first, the function walks the target raw source directory structure, and duplicates it in the raw output directory. Then it walks the target raw source files, looking for each filename in graphics_to_apply's keyset, or one of the properties graphics_overwrite or graphics_ignore. 
        * If it finds the filename in graphics_overwrite, it copies the file directly from the corresponding place in the graphics source directory.
        * If it finds the filename in graphics_ignore, or doesn't find the filename at all, it copies the file directly from the corresponding place in the target raw source directory.
        * If it finds the filename in graphics_to_apply's keyset, it opens the file in the target raw source directory, creates and opens a corresponding file in the raw output directory, and walks through the target raw source file a line at a time, constructing the modified file.
    """
    
    verbose = config.properties[config.DEBUG][1]
    properties = config.properties
    if verbose:
        print("Writing modified raws...")
    for root, dirs, files in os.walk(raws_sourcedir):
        # Create directories so we don't have any issues later on
        for dir in dirs:
            targetdir = os.path.join(root,dir)
            targetdir = outputdir + targetdir[len(raws_sourcedir):]
            if not os.path.exists(targetdir):
                if verbose:
                    print("Creating output directory",dir)
                os.mkdir(targetdir)
        for file in files:
            targetpath = os.path.join(root,file)
            targetpath = outputdir + targetpath[len(raws_sourcedir):]
            if parsing.path_compatible(targetpath,properties[config.GRAPHICS_OVERWRITE_LIST][1:]):
                if verbose:
                    print("Skipping",file,": graphics overwrite TBI.")
                pass
            elif parsing.path_compatible(targetpath,properties[config.GRAPHICS_IGNORE_LIST][1:]):
                if verbose:
                    print("Skipping",file,": graphics ignore TBI.")
                pass
            elif file not in graphics_to_apply.keys():
                if verbose:
                    print("No graphics to apply to",file,". Copying from target source...")
                targetpath = shutil.copyfile(os.path.join(root,file),targetpath)
                if verbose:
                    print(file,"copied.")
            else:
                if verbose:
                    print("Merging graphics into",file,"...")
                curr_dict = graphics_to_apply[file]
                curr_node = None
                targetfile = open(targetpath,'wt',encoding='cp437')
                sourcefile = open(os.path.join(root,file),'rt',encoding='cp437')
                linecount = 0
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
                                    if verbose:
                                        print("Replacing",tag,"with",replacement,"at line",linecount,".")
                                    modified_line = modified_line.replace(tag,replacement)
                                else:
                                    if verbose:
                                        print("Removing tag",tag,"at line",linecount,".")
                                    to_remove = "[" + tag + "]"
                                    modified_line = modified_line.replace(to_remove,"")
                                #modified_line = modified_line[:-1] + " (BAMM)\n"
                            additional.extend(matching_node.pop_addl())
                    
                    targetfile.writelines(modified_line)
                    for tag_node in additional:
                        linecount = linecount + 1
                        if verbose:
                            print("Adding tag",tag_node._tag,"at line",linecount,".")
                        line_to_write = "[" + tag_node._tag + "]\n"# (BAMM)\n"
                        targetfile.writelines(line_to_write)

                targetfile.flush()
                if verbose:
                    print("Finished outputting",file,".")
                targetfile.close()
                sourcefile.close()
    if verbose:
        print("All files written.")

def walk_rawfiles_into_tagnode_collection(directory):
    """Load the graphics-relevant content of raw files into memory.
    
    directory is a directory containing the raw files you want to load into memory. None of the files may have duplicate names, even if they're in different sub-folders.
    
    The function returns a dictionary of string:dict{string:TagNode}. The outer key is a filename which contains some graphics-relevant content. The inner key is the tag corresponding with a top-level TagNode in that file, and maps to that TagNode.
    
    This format is the expected input format of both parameters of bind_graphics_to_targets(graphics_nodes,target_nodes).
    """
    verbose = config.properties[config.DEBUG][1]
    node_collection = {}
    for root, dirs, files in os.walk(directory):
        for rawfile in files:
            # Only look at .txt files
            if '.txt' not in rawfile:
                if verbose:
                    print("Skipping file",rawfile,"...")
                continue
            if verbose:
                print("Loading graphics tags from",rawfile,"...")
            global template_tree
            # curr_template_node keeps track of what format of tag we've most recently seen, and thus what's valid next
            curr_template_node = template_tree
            # curr_real_node keeps track of the tag we stored that corresponds to the most local instance of curr_template_node.
            curr_real_node = None
            tarpath = os.path.join(root, rawfile)
            openfile = open(tarpath,encoding='cp437')
            for line in openfile:
                for tag in parsing.tags(line):
                    matching_node = curr_template_node.find_match(tag)
                    if matching_node != None:
                        curr_template_node = matching_node
                        if curr_real_node == None or matching_node._tag in template_tree._children:
                            curr_real_node = TagNode(rawfile,matching_node,tag)
                        else:
                            while curr_real_node != None and matching_node._tag not in curr_real_node._template._children:
                                curr_real_node = curr_real_node._parent
                            curr_real_node = TagNode(rawfile,matching_node,tag,curr_real_node)
                        if rawfile not in node_collection:
                            node_collection[rawfile] = { }
                        if curr_real_node._parent == None:
                            node_collection[rawfile][tag] = curr_real_node

            openfile.close()
            if verbose:
                print("Finished processing",rawfile,".")
    return node_collection

def bind_graphics_to_targets(graphics_nodes,targets_nodes):
    """Associate two collections of TagNodes with each other, in preparation for merging.
    
    graphics_nodes and targets_nodes are dicts of type string:dict{string:TagNode}, where the outer key is a file name, the inner keys are tags associated with top-level TagNodes, and the TagNodes are of course those same top-level TagNodes. These string:string:TagNodes are expected to be produced by walk_rawfiles_into_tagnode_collection. 
    
    The function returns a similarly-formatted dict of BoundNodes, in the format string:dict{string:BoundNode}, where the outer key is a file name, the inner key is the tag associated with the target_nodes of top level BoundNodes, and the BoundNodes are, as usual, those BoundNodes.
    
    The BoundNodes in the return dict are generated from the two arguments, by matching up TagNodes from graphics_nodes and targets_nodes based on their filenames, templates, and parents. If a TagNode in either argument has no corresponding TagNode in the other, it is dropped if it has children or non-graphical content. If neither of those is the case, it's saved as an "additional" graphics tag to be added or removed in the conversion.
    """
    verbose = config.properties[config.DEBUG][1]
    if verbose:
        print("Binding graphics source tags to target tags...")
    to_return = {}
    for filename in targets_nodes.keys():
        # Files which both share, both have found graphics in, and haven't been put in the return dict yet.
        if filename in graphics_nodes.keys() and filename not in to_return.keys():
            if verbose:
                print("Binding tags for",filename,"...")
            to_return[filename] = {} 
            for top_level_tag in targets_nodes[filename].keys():
                # Top level tags which both share, both have found graphics in, and haven't been put in the return dict yet.
                if top_level_tag in graphics_nodes[filename] and top_level_tag not in to_return[filename].keys():
                    # Create new BoundNode tree and put it in the return dict.
                    to_return[filename][top_level_tag] = BoundNode(targets_nodes[filename][top_level_tag],graphics_nodes[filename][top_level_tag])
            if verbose:
                print(filename,"tags bound.")
    if verbose:
        print("Tag binding complete.")
    return to_return






                

class TreeNode():
    """Parent class for the other Node classes.
    
    Contains default implementations of common Tree functionality.
    
    Members: 
        self._parent = the parent TreeNode of this TreeNode. Any given subclass of TreeNode should only have TreeNodes of its own type as _parent.
        self._tag = The string that this node represents. This should be overridden and re-defined by subclasses.
        self._children = A dict of type string:TreeNode, where the key is the child's ._tag property. 
    """
    
    def __init__(self,parent=None):
        self._parent = parent
        self._children = {}
        self._tag = None
        #if parent != None:
        #    parent.add_child(self)
        
    def add_child(self, child_node):
        self._children[child_node._tag] = child_node
    
    def find_match(self, tag):
        curr_node = self
        matching_node = None
        out_of_parents = False
        while matching_node == None and not out_of_parents:
            #matching_node = curr_node.get_template_match(tag)[0]
            #if matching_node == None:
            matching_node = curr_node.get_child(tag)
            if curr_node._parent == None:
                out_of_parents = True
            else:
                curr_node = curr_node._parent
        return matching_node
    
    def get_child(self, tag):
        if tag in self._children.keys():
            return self._children[tag]
        else:
            return None
        

class TemplateNode(TreeNode):

    #self._tag #string
    #self._children    # dict of TemplateNodes
    #self._childref        # dict of lists of TemplateNodes where the key is the first token
    #self._parent    # TemplateNode
    #self._is_graphics_tag    # Boolean

    #string does not contain the character '|'.
    def __init__(self, parent, string=""):
        TreeNode.__init__(self,parent)
        self._is_graphics_tag = False
        self._childref = {}
        self._tag = None
        global template_tree
        if parent == None:
            self._parent = None
            template_tree = self
        else:
            if template_tree == None:
                self._parent = TemplateNode(None, "")
            else:
                self._parent = parent

            self._tag = string

            parent.add_child(self)

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

    def get_child(self, tag):
        verbose = config.properties[config.DEBUG][1]
        if tag in self._children.keys():
            return self._children[tag]
        else:
            return_possibilities = []
            first_token = tag.split(':')[0]
            if first_token in self._childref:
                for child in self._childref[first_token]:
                    return_node = child.get_template_match(tag)
                    if return_node != None:
                        return_possibilities.append(child)
                if len(return_possibilities) == 1:
                    return return_possibilities[0]
                elif len(return_possibilities) == 0:
                    return None
                else:
                    # TODO error handling
                    if verbose:
                        print("Found more than one matching child. Matching children are:")
                        for poss in return_possibilities:
                            print(poss)
                    return return_possibilities[0]
            else:
                return None

    # This tells if a single tag matches a single tag; that is, it assumes we've got one element of the |-separated list 
    def get_template_match(self, tag_to_compare):
        verbose = config.properties[config.DEBUG][1]
        if self._tag == None:
            return None
        template_token_bag = []
        template_token_bag.append(self._tag.split(':'))
        candidate_tokens = tag_to_compare.split(':')

        ii = 0
        while ii < len(candidate_tokens) and len(template_token_bag) > 0:
            good_to_go = False
            for var in template_token_bag:
                if ii >= len(var):
                    template_token_bag.remove(var)
                elif '&' == var[ii] or '?' == var[ii] or '$' == var[ii] or var[ii] == candidate_tokens[ii]:
                    # This case is an auto-pass
                    good_to_go = True
                else:
                    if '&' in var[ii] or '?' in var[ii] or '$' in var[ii]:
                        varii_type = var[ii][0]
                        varii_range = var[ii][2:var[ii].index(')')].split(',')
                        # If len(varii_range) == 1 then we have a range of format (x,), indicating any number of :'s
                        if len(varii_range[1]) == 0:
                            varii_range[1] = len(candidate_tokens)-len(var) + 1
                        # For every possible length (the +1 is because range is exclusive-end and my notation is inclusive-end)
                        for jj in range(int(varii_range[0]),int(varii_range[1])+1):
                            # Make a copy of var
                            new_var = var[:]
                            # Remove the range item
                            del new_var[ii]
                            # Replace it with (one of the possible lengths) times the multiplied symbol
                            # If jj is 0 the range item is just removed
                            for kk in range(0,jj):
                                new_var.insert(ii,varii_type)
                            # Place the new variant in the token bag for evaluation
                            template_token_bag.append(new_var)
                    # No counting, there is a new template_token_bag[ii]
                    template_token_bag.remove(var)
            if good_to_go:
                ii += 1
        for tag in template_token_bag:
            if len(tag) != len(candidate_tokens):
                template_token_bag.remove(tag)
        if len(template_token_bag) == 0:
            return None
        elif len(template_token_bag) == 1:
            return template_token_bag
        else:
            # TODO error handling
# TODO plant GROWTH_PRINTs are throwing this when they end and there are templates of size n and n+1, fix that up plz
            if verbose:
                print("More than one template matched.\nTag:",tag_to_compare,"Matches:")
                for template in template_token_bag:
                    print(template)
            # Technically this does in fact have a matching template
            return template_token_bag

    def how_many_generations(self):
        temp_node = self
        count = -1
        global template_tree
        while temp_node != template_tree:
            temp_node = temp_node._parent
            count = count + 1
        return count

class TagNode(TreeNode):
    
    def __init__(self,filename,template,tag,parent=None):
        TreeNode.__init__(self, parent)
        self._tag = tag
        self._filename = filename
        self._template = template
        self._children = {}
        self._pat_children = {}
        self._pattern = None
        self._pattern = self.get_pattern()

        if parent != None:
            parent.add_child(self)

    def add_child(self, child_tag_node):
        self._children[child_tag_node._tag] = child_tag_node
        self._pat_children[child_tag_node.get_pattern()] = child_tag_node

    def apply_graphics(self, graphics_node):
        verbose = config.properties[config.DEBUG][1]
        if graphics_node == None:
            return None
        tags = self._tag.split(':')
        graphics = graphics_node._tag.split(':')
        tag_template = self._template.get_template_match(self._tag)[0]
        merged = []
        graphics_template = self._template.get_template_match(graphics_node._tag)[0]
        #    print("Graphics cannot be applied from",graphics_node._tag,"onto",self._tag)

        for ii in range(0,len(tag_template)):
            if tag_template[ii] != graphics_template[ii]:
                if verbose:
                    print("Graphics cannot be applied from",graphics_node._tag,"onto",self._tag,"because their templates do not match.")
            elif tag_template[ii] != '&' and tag_template[ii] != '?':
                if tags[ii] != graphics[ii]:
                    if verbose:
                        print("Tags are not compatible because token",ii,"does not match. Target:",tags[ii]," Graphics:",graphics[ii])
                else:
                    merged.append(tags[ii])
            elif tag_template[ii] == '&':
                merged.append(tags[ii])
            elif tag_template[ii] == '?':
                merged.append(graphics[ii])
            else:
                if verbose:
                    print("This block should never be reached. Big problem in TagNode.apply_graphics.")

        return ":".join(merged)

    # Too much work
    # def compatible_with(self, graphics_tag_node):
    #    return self._template.resolve(self._tag,graphics_tag_node._tag) != None

    def get_pattern(self):
        verbose = config.properties[config.DEBUG][1]
        if self._pattern == None:
            to_return = self._tag.split(':')
            tag_tokens = self._tag.split(':')
            template_possibilities = self._template.get_template_match(self._tag)
            if len(template_possibilities) != 1:
                if verbose:
                    print("Tag",self._tag,"has",len(template_possibilities),"possible configurations:")
                    for config_ in template_possibilities:
                        print(config_,', ')
            else:
                for ii in range(0,len(tag_tokens)):
                    if template_possibilities[0][ii] in [tag_tokens[ii],'$']:
                        to_return[ii] = tag_tokens[ii]
                    elif template_possibilities[0][ii] in ['?','&']:
                        to_return[ii] = template_possibilities[0][ii]
                    elif verbose:
                        print("Tag does not match its own template!! Tag:",self._tag,"; Template:",self._template._template_tag)
            self._pattern = ":".join(to_return)
        return self._pattern

    def aligns_with(self,other_tag):
        return self._template == other_tag._template and self.get_pattern() == other_tag.get_pattern()
    
    def is_graphics_tag(self):
        return self._template._is_graphics_tag

class BoundNode(TreeNode):
    def __init__(self,target_node,graphics_node,parent=None):
        TreeNode.__init__(self, parent)
        self._tag = target_node._tag
        self._popped_children = {}
        self._additional = []
        self._are_addl_popped = False
        self._target_node = target_node
        self._graphics_node = graphics_node
        if parent != None:
            parent.add_child(self)
        else:
            self.create_child_nodes()

    def add_child(self, child_node):
        self._children[child_node._target_node._tag]=child_node
        self._popped_children[child_node._target_node._tag]=False

    def create_child_nodes(self):
        # Children with pattern keys in both target & graphics
        for shared_key in set(self._target_node._pat_children.keys()).intersection(set(self._graphics_node._pat_children.keys())):
            new_node = BoundNode(self._target_node._pat_children[shared_key],self._graphics_node._pat_children[shared_key],self)
            self.add_child(new_node)
            new_node.create_child_nodes()
        # Children with pattern keys in target but not in graphics
        for target_key in set(self._target_node._pat_children.keys()) - set(self._graphics_node._pat_children.keys()):
            if self._target_node._pat_children[target_key].is_graphics_tag() and not ('&' in self._target_node._template._tag or '$' in self._target_node._template._tag):
                self.add_child(BoundNode(self._target_node._pat_children[target_key],None,self))
        # Children with pattern keys in graphics but not in target
        for graphics_key in set(self._graphics_node._pat_children.keys()) - set(self._target_node._pat_children.keys()):
            graphics_in_question = self._graphics_node._pat_children[graphics_key]
            if graphics_in_question.is_graphics_tag():
                self._additional.append(graphics_in_question)
        # End

    def are_all_children_popped(self):
        to_return = True
        for child in self._popped_children.keys():
            to_return &= self._popped_children[child]
        return to_return
        
    def pop_addl(self):
        to_return = []
        # If this hasn't had its additionals popped and is ready to pop
        if (not self._are_addl_popped):
            self._are_addl_popped = True
            to_return.extend(self._additional)
        if self._parent != None:
            to_return.extend(self._parent.pop_addl())
        return to_return

    def get_merged(self):
        return self._target_node.apply_graphics(self._graphics_node)

    def pop_child(self, target_tag):
        verbose = config.properties[config.DEBUG][1]
        if target_tag not in self._children.keys():
            return self
        else:
            if self._popped_children[target_tag] and verbose:
                print("Popping tag that has already been popped:",target_tag,"child of",self._tag)

            self._popped_children[target_tag] = True
            return self._children[target_tag]
        
    def pop_self(self):
        verbose = config.properties[config.DEBUG][1]
        if self._parent != None:
            also_self = self._parent.pop_child(self._tag)
            if also_self != self and verbose:
                print("Big problem: Bound Node with _tag",self._tag,"is not its parent's ._children[",self._tag,"]")
        return self
    
    def is_there_a_difference(self):
        if self._graphics_node == None:
            return True
        elif self._target_node._tag == self._graphics_node._tag:
            return False
        else:
            return True