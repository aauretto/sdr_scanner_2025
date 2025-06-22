from hw_interface.font_manager import FontManager

class MenuOption():

    def __init__(self, name, action):
        self.name = name
        self.action = action

class Menu():

    def __init__(self, title: str, opsPerScreen: int = 3):
        """
        Class that implements a drawable menu

        Parameters
        ----------
        Title: str
            Title of the menu
        opsPerScreen: int
            Number of elements we can scroll through before the menu elements themselves 
            need to move. This should be the number of elements that we can fit on a
            single screen.
        """
        self.__title = title
        self.__selected = 0
        self.__options = []
        self.__topDisplayed = 0
        self.__opsPerScreen = opsPerScreen

        self.__fontmgr = FontManager()

    def register_option(self, MenuOption):
        self.__options.append(MenuOption)

    def scroll_down(self):
        if self.__selected < len(self.__options):
            self.__selected += 1
            # Check if we need to scroll entire menu
            if self.__selected - self.__topDisplayed > self.__opsPerScreen - 1:
                self.__topDisplayed += 1
    def scroll_up(self):
        if self.__selected > 0:
            self.__selected = (self.__selected - 1)
            # Check if we need to scroll entire menu
            if self.__selected < self.__topDisplayed:
                self.__topDisplayed -= 1
    def select(self):
        print(f"{self.__topDisplayed=} / {self.__selected=}")
        return self.__options[self.__selected].action
    
    
    def draw(self, draw):
        # Draw title
        draw.line((0, 20, 127, 20), fill="white")
        draw.text((5,5), self.__title, font=self.__fontmgr.load_font(10), fill="white")

        for pos, opt in enumerate(range(self.__topDisplayed, len(self.__options))):
            if opt == self.__selected:
                prefix = ">"
            else:
                prefix = " "
                
            draw.text((5,25 + pos * 12), f"{prefix}{self.__options[opt].name}", font=self.__fontmgr.load_font(8), fill="white")