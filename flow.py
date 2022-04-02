import re
import pydot
from optparse import OptionParser
import backward


class GraphManager(object):
    """ pydot graph objects manager """

    def __init__(self):
        self.graph = pydot.Dot(graph_type='digraph', simplify=True)

    def add_edge(self, b1, b2, label="CONT"):
        """ join two pydot nodes / create nodes edge """
        # Edge color based on label text
        if label == 'false':
            ecolor = "red"
        elif label == 'true':
            ecolor = 'green'
        elif label == 'exception':
            ecolor = 'orange'
        elif label == 'try':
            ecolor = 'blue'
        else:
            ecolor = 'gray'
        # node shape based on block type (First or Last instruction)
        nodes = [None, None]
        blocks = [b1, b2]
        for i in range(2):
            if Block.isTag(blocks[i].instructions[-1], 'isConditional'):
                ncolor = "cornflowerblue"
            elif Block.isTag(blocks[i].instructions[0], 'isLabel'):
                ncolor = "tan"
            elif Block.isTag(blocks[i].instructions[-1], 'isJump'):
                ncolor = "darkgreen"
            elif Block.isTag(blocks[i].instructions[-1], 'isCall'):
                ncolor = "lightyellow4"
            else:
                ncolor = "mediumaquamarine"
            nodes[i] = pydot.Node(b1.label, color=ncolor, style="filled", shape="box", fontname="Courier", fontsize="8")
            bis = "%s\l%s\l" % (blocks[i].label, "\l".join(blocks[i].instructions))
            nodes[i].set_name(bis)
            self.graph.add_node(nodes[i])

        ed = pydot.Edge(nodes[0], nodes[1], color=ecolor, label=label, fontname="Courier", fontsize="8",
                        arrowhead="open")
        self.graph.add_edge(ed)

    def draw(self, name):
        self.graph.write_png(name)


class Block(object):
    """ Sequential group of instructions """

    def __init__(self, parent_class=None, parent_method=None, label=None, instructions=None):
        """
            Parameters:
                parent_class: Class where our code is located.
                parent_method: Class method where our code is located.
                label: Block identifier (class name[space]method name[space]first line offset).
                instructions: list raw instructions
                targets: Code flow changes targets, if any.
        """
        self.parent_class = parent_class
        self.parent_method = parent_method
        self.label = label
        self.instructions = instructions
        self.targets = []  #child
        self.parent = []
        self.child = []
        self.search_flag = False
        self.hasPi = False


    @staticmethod
    def isTag(inst, ttype):
        """ Indicates whether the specified code line contains an known instruction. """
        if ttype == 'isMethodBegin':
            match = re.search("^.method ", inst)
        elif ttype == 'isMethodEnd':
            match = re.search("^.end method", inst)
        elif ttype == 'isJump':
            match = re.search("^goto", inst)
        elif ttype == 'isConditional':
            match = re.search("^if-", inst)
        elif ttype == 'isCatch':
            match = re.search("^.catch ", inst)
        elif ttype == 'isLabel':
            # match = re.search("^\:" , inst) and ((not re.search("^\:try" , inst)) and (not re.search("^\:catch" , inst)))
            match = re.search("^\:", inst)
        elif ttype == 'isReturn':
            match = re.search("^return-", inst)
        elif ttype == 'isCall':
            match = re.search("^invoke-", inst)
        else:
            match = None
        if match:
            return True
        else:
            return False

    def add_inst(self, inst):
        """ Just add one instruction to our set of instructions. """
        self.instructions.append(inst)

    def isNeighbor(self, block):
        """ Specified block is at the same class and method ? """
        return (block.parent_class == self.parent_class) and (block.parent_method == self.parent_method)

    def getLength(self, inc=0):
        return len(self.instructions) + inc


class BlockFactory(object):
    def __init__(self):
        self.blocks = []

    def add(self, blk):
        global graph
        """ Add the block to our blocks list if it is not present and have at least one instruction. """
        if (not (blk in self.blocks)) and (len(blk.instructions) > 0):
            self.blocks.append(blk)

    def add_before(self, label=None, inst=None, block=None, pclass=None, pmethod=None):
        """ Add instruction to the current block, and then add this to our blocks list. """
        if backward.check_exist(inst, " :Pendingintent created"):
            block.hasPi = True
        block.add_inst(inst)
        self.add(block)
        return Block(label=label, instructions=[], parent_class=pclass, parent_method=pmethod)

    def add_after(self, label=None, inst=None, block=None, pclass=None, pmethod=None):
        """ Add the block to our list, and make a new one with the specified instructions. """
        self.add(block)
        b = Block(label=label, instructions=[inst], parent_class=pclass, parent_method=pmethod)
        return b

    @staticmethod
    def xtractBlock(classfile, functionname):
        """ split smali class file into method/s code lines. """
        # read class file contents
        fh = open(classfile, "r")
        fc = fh.read()
        fh.close()
        # extract method raw lines
        methods = []
        for m in re.findall("\.method\s(.*?)\n(.*?)\.end\smethod", fc, re.DOTALL):
            if functionname is not None:
                if m[0].split(' ')[-1].split('(')[0] == functionname:
                    methods.append(m)
                    break
            else:
                methods.append(m)
        # remove empty lines
        if len(methods) == 0:
            return None
        else:
            ret = []
            for m in methods:
                instructions = []
                for inst in m[1].split("\n"):
                    if len(inst) > 0 and (not backward.check_exist(inst, ".line")):
                        instructions.append(inst.lstrip())
                mname = m[0].split(' ')[-1].split('(')[0]
                ret.append((mname, instructions))
            # All done!
            return ret

    @staticmethod
    def xtractBlockfromLine(classfile, line):
        """ split smali class file into method/s code lines. """
        # read class file contents
        line = int(line)
        with open(classfile, 'r') as out:
            content = out.readlines()
        up_boundary, down_boundary, method_info = backward.find_boundary(content, line)
        return_method_info = method_info.rpartition(" ")[2]
        content[line - 1] = content[line - 1].strip() + " :Pendingintent created"
        #print(content[line - 1] )
        ret = []
        instructions = []
        mname = content[up_boundary - 1].split(' ')[-1].split('(')[0]
        check_line = up_boundary + 1
        check_line_content = content[check_line - 1].strip("\n")
        while check_line < down_boundary - 1:
            if len(check_line_content) > 0 and (not backward.check_exist(check_line_content, ".line") and not (check_line_content == '\n')):
                instructions.append(check_line_content.strip())
            check_line += 1
            check_line_content = content[check_line]
        ret.append((mname, instructions))
        # All done!
        return ret, return_method_info

    @staticmethod
    def splitBlock(blk, classn, methodn, pos, lenInc, iset, i):
        blockLen = len(blk.instructions) + lenInc #加上之前指令的长度
        incrementalLabel = "%s %s %d" % (classn, methodn, pos + blockLen) #新的标签
        if not Block.isTag(i, 'isCall'):
            if " :Pendingintent created" in i:
                i = i.rpartition(" :Pendingintent created")[0]
            positionalLabel = "%s %s %d" % (classn, methodn, iset.index(i.split(' ')[-1]) + 1)
        else:
            lindex = int(blk.label.split(' ')[-1]) + len(blk.instructions) #如果是方法调用语句
            positionalLabel = " ".join(blk.label.split(' ')[:-1]) + " " + str(lindex + 1)
        return (incrementalLabel, positionalLabel)


def method2garph(classname, methodInstructions):
    graph_mgr = GraphManager()
    methods = []
    if methodInstructions is not None:
        for mnam, minst in methodInstructions:
            methods.append((classname, mnam, minst))

    ## linear pass 1
    # split method code block into smaller blocks (calls/jumps/conditionals/labeled/catch)
    # calculate block target/s.
    factory = BlockFactory()  # 初始化self.blocks = []
    for (cname, mname, minsts) in methods:
        # default initial block
        b = Block(label=cname + " " + mname + " 1", instructions=[], parent_class=cname, parent_method=mname)  # 初始化块
        # 对于不同的语句有不同的处理方式：
        # 普通语句直接加入到块的instructions中
        # lable语句： :goto_ :cond_ :将包含之前的指令的块添加到factory中并返回新的包含该指令的块
        # 其他语句（跳转，条件）：将该语句添加到块中然后将该块添加到factory中并返回新的空块
        for i2 in minsts:  # ins
            instrPos = minsts.index(i2) + 1
            blockPos = int(b.label.split(' ')[-1])  # label：类名+方法名 + 1 blockPos:1
            # process different flag in ins
            if Block.isTag(i2, 'isJump'):
                (incLabel, posLabel) = BlockFactory.splitBlock(b, cname, mname, blockPos, 1, minsts, i2)
                b.targets = [('jump', posLabel)]  # child
                b = factory.add_before(label=incLabel, inst=i2, block=b, pclass=cname,
                                       pmethod=mname)  # 将指令添加到块中（instructions）然后把块添加到BlockFactory中
            elif Block.isTag(i2, 'isConditional'):
                (incLabel, posLabel) = BlockFactory.splitBlock(b, cname, mname, blockPos, 1, minsts, i2)
                b.targets = [('true', posLabel), ('false', incLabel)]
                b = factory.add_before(label=incLabel, inst=i2, block=b, pclass=cname, pmethod=mname)
            elif Block.isTag(i2, 'isLabel'):
                (incLabel, posLabel) = BlockFactory.splitBlock(b, cname, mname, blockPos, 0, minsts, i2)
                b.targets = [('cont', incLabel)]
                b = factory.add_after(label=incLabel, inst=i2, block=b, pclass=cname,
                                      pmethod=mname)  # 将包含之前的指令的块加入到factory中并返回一个包含此指令新的块
            elif Block.isTag(i2, 'isCatch'):
                (incLabel, posLabel) = BlockFactory.splitBlock(b, cname, mname, blockPos, 1, minsts, i2)
                b.targets = [('exception', posLabel), ('try', incLabel)]
                b = factory.add_before(label=incLabel, inst=i2, block=b, pclass=cname, pmethod=mname)
            elif Block.isTag(i2, 'isCall'):
                (incLabel, posLabel) = BlockFactory.splitBlock(b, cname, mname, blockPos, 1, minsts, i2)
                b.targets = [('on return', posLabel)]  #
                b = factory.add_before(label=incLabel, inst=i2, block=b, pclass=cname, pmethod=mname)  # 将指令添加到块中
            else:
                b.add_inst(i2)  # 将指令添加到块（instructions）中
        factory.add(b)

    ## linear pass 2
    # joining graph nodes !
    for b1 in factory.blocks:
        for lbl, target in b1.targets:
            for b2 in factory.blocks:
                if b2.label == target:
                    b1.child.append(b2)
                    b2.parent.append(b1)
                    graph_mgr.add_edge(b1, b2, lbl)
                    break


    return factory


if __name__ == '__main__':

    ## Parsing command line options
    modes = ['XRefTo', 'XRefFrom', 'XRefBoth']
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option("-c", "--class", action="store", type="string", dest="filename",
                      help="Smali class file.")
    parser.add_option("-m", "--method", action="store", type="string", dest="methodname",
                      help="Class method to analyze).")

    ## Handling command line options errors.
    (options, args) = parser.parse_args()
    if (not options.filename):
        parser.error("option -c is mandatory.")

    graph_mgr = GraphManager()
    methods = []
    classname = "/".join(options.filename.split('.')[0].split('/')[1:])
    methodInstructions = BlockFactory.xtractBlock(options.filename, options.methodname) #返回[（函数名, 函数中的指令['1','2']）]
    if methodInstructions is not None:
        for mnam, minst in methodInstructions:
            methods.append((classname, mnam, minst))

    ## linear pass 1
    # split method code block into smaller blocks (calls/jumps/conditionals/labeled/catch)
    # calculate block target/s.
    factory = BlockFactory() #初始化self.blocks = []
    for (cname, mname, minsts) in methods:
        # default initial block
        b = Block(label=cname + " " + mname + " 1", instructions=[], parent_class=cname, parent_method=mname) #初始化块
        # 对于不同的语句有不同的处理方式：
        # 普通语句直接加入到块的instructions中
        # lable语句： :goto_ :cond_ :将包含之前的指令的块添加到factory中并返回新的包含该指令的块
        # 其他语句（跳转，条件）：将该语句添加到块中然后将该块添加到factory中并返回新的空块
        for i2 in minsts: #ins
            instrPos = minsts.index(i2) + 1
            blockPos = int(b.label.split(' ')[-1]) #label：类名+方法名 + 1 blockPos:1
            #process different flag in ins
            if Block.isTag(i2, 'isJump'): #判断是不是跳转goto
                (incLabel, posLabel) = BlockFactory.splitBlock(b, cname, mname, blockPos, 1, minsts, i2)
                b.targets = [('jump', posLabel)] #child
                b = factory.add_before(label=incLabel, inst=i2, block=b, pclass=cname, pmethod=mname) #将指令添加到块中（instructions）然后把块添加到BlockFactory中
            elif Block.isTag(i2, 'isConditional'):
                (incLabel, posLabel) = BlockFactory.splitBlock(b, cname, mname, blockPos, 1, minsts, i2)
                b.targets = [('true', posLabel), ('false', incLabel)]
                b = factory.add_before(label=incLabel, inst=i2, block=b, pclass=cname, pmethod=mname)
            elif Block.isTag(i2, 'isLabel'):
                (incLabel, posLabel) = BlockFactory.splitBlock(b, cname, mname, blockPos, 0, minsts, i2)
                b.targets = [('cont', incLabel)]
                b = factory.add_after(label=incLabel, inst=i2, block=b, pclass=cname, pmethod=mname) #将包含之前的指令的块加入到factory中并返回一个包含此指令新的块
            elif Block.isTag(i2, 'isCatch'):
                (incLabel, posLabel) = BlockFactory.splitBlock(b, cname, mname, blockPos, 1, minsts, i2)
                b.targets = [('exception', posLabel), ('try', incLabel)]
                b = factory.add_before(label=incLabel, inst=i2, block=b, pclass=cname, pmethod=mname)
            elif Block.isTag(i2, 'isCall'):
                (incLabel, posLabel) = BlockFactory.splitBlock(b, cname, mname, blockPos, 1, minsts, i2)
                b.targets = [('on return', posLabel)] #
                b = factory.add_before(label=incLabel, inst=i2, block=b, pclass=cname, pmethod=mname) #将指令添加到块中
            # elif Block.isTag(i2, 'isSwitch'):
            #     (incLabel, posLabel) = BlockFactory.splitBlock(b, cname, mname, blockPos, 1, minsts, i2)
            #     b.targets = [('jump', posLabel)]  # child
            #     b = factory.add_before(label=incLabel, inst=i2, block=b, pclass=cname,
            #                            pmethod=mname)  # 将指令添加到块中（instructions）然后把块添加到BlockFactory中
            else:
                b.add_inst(i2) #将指令添加到块（instructions）中
        factory.add(b)

    ## linear pass 2
    # joining graph nodes !
    for b1 in factory.blocks:
        for lbl, target in b1.targets:
            for b2 in factory.blocks:
                if b2.label == target:
                    b1.child.append(b2)
                    b2.parent.append(b1)
                    graph_mgr.add_edge(b1, b2, lbl)
                    break




