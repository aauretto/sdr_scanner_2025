class Menu():

    def __init__(self, title):
        self.__title = title
        self.__selected = 0
        self.__options = []
    
    def register_option(self, name, onClick):
        # TODO Later
        pass



    def scroll_down(self):
        self.__selected = (self.__selected + 1) % len(self.__options)
    def scroll_up(self):
        self.__selected = (self.__selected - 1) % len(self.__options)
    def select(self):
        return self.__options[self.__selected]

    
    def draw(self, draw):

    
