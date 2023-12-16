import re
from os.path import join


class Processor:

    def __init__(self, ctx):
        self.log = ctx.log
        self.cfg = ctx.cfg
        self.ctx = ctx

    def processText(self, txt):
        outputText = []
        regEx = re.compile("@T=[a-zA-z0-9]+.html")
        resGrp = regEx.search(txt)
        while resGrp is not None:
            outputText.append(txt[:resGrp.start()])
            template = txt[resGrp.start()+3:resGrp.end()]
            outputText += self._resolve(template)
            txt = txt[resGrp.end():]
            resGrp = regEx.search(txt)
        outputText.append(txt)
        return ''.join(outputText)

    def _resolve(self, template):
        outputText = []
        file = join(self.cfg.general_templatesDirectory, template)
        with open(file, 'r') as f:
            data = f.read()
        regExDirective = re.compile("#![A-Z]+!#")
        resGrp = regExDirective.search(data)
        if resGrp is not None:
            if data[resGrp.start():resGrp.end()] == "#!FOREACHAIRTAG!#":
                # process the remaining part for each airtag
                data = data[resGrp.end():]
                regEx = re.compile("##[A-Z]+##")
                for a in self.ctx.airtags.values():
                    tmpData = data
                    resGrp = regEx.search(tmpData)
                    tmp = []
                    while resGrp is not None:
                        tmp.append(tmpData[:resGrp.start()])
                        tag = tmpData[resGrp.start():resGrp.end()]
                        tmp.append(a.resolveTag(tag))
                        tmp.append(tmpData[resGrp.end():])
                        tmpData = ''.join(tmp)
                        tmp = []
                        resGrp = regEx.search(tmpData)
                    outputText.append(tmpData)
        return outputText

