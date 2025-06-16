from hw_interface.font_manager import FontManager

class MenuOption():

    def __init__(self, name, action):
        self.name = name
        self.action = action

class Menu():

    def __init__(self, title):
        self.__title = title
        self.__selected = 0
        self.__options = []

        self.__fontmgr = FontManager()
    
    def register_option(self, MenuOption):
        self.__options.append(MenuOption)

    def scroll_down(self):
        if self.__selected < len(self.__options):
            self.__selected = (self.__selected + 1)
    def scroll_up(self):
        if self.__selected > 0:
            self.__selected = (self.__selected - 1)
    def select(self):
        return self.__options[self.__selected]

    
    def draw(self, draw):
        # Draw title
        draw.line((0, 20, 127, 20), fill="white")
        draw.text((5,5), self.__title, font=self.__fontmgr.load_font(10), fill="white")

        for i in range(len(self.__options)):
            
            if i == 0:
                prefix = ">"
            else:
                prefix = " "
                
            draw.text((5,25 + i * 12), f"{prefix}{self.__options[(self.__selected + i) % len(self.__options)].name}", font=self.__fontmgr.load_font(8), fill="white")
            
