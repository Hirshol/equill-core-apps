from sdk.dialog_overlay import DialogOverlay
from sdk.widgets.password import Password
from sdk.widgets.button import Button
from sdk.widgets.label import Label
from sdk.doc_page import DocumentPage
from sdk import display

class PasswordDialog(DialogOverlay):
    def __init__(self, text, current_page, width=400, font_size=16):
        self._h_offset = 20
        self.font_size = font_size
        self.text = text
        self.font = display.get_font(self.font_size)
        self.text_image = display.draw_word_wrap(self.text, width - 2 * self._h_offset, 
                                                 font=self.font)
        self._label_height = self._password_height = 40
        self._button_height = 40
        self._v_offset = 20
        self.height = self._v_offset + self.text_image.size[1] + self._password_height + \
            self._v_offset + self._button_height + 80
        gui_page = current_page.gui_page if isinstance(current_page, DocumentPage) else current_page
        DialogOverlay.__init__(self, width, self.height, parent_window = gui_page)

    def load_gui(self):
        DialogOverlay.load_gui(self)
        y = self._v_offset
        x = self._h_offset
        query = 'Password? '
        password_image = display.draw_word_wrap(query, 
                                             display.get_text_size(query, 20), 
                                                display.get_font(20))
        self.working_image().paste(self.text_image, (x,y))
        y += self.text_image.size[1] + self._v_offset
        query_w = password_image.size[0]
        self.password = Password('', self.w - (query_w + self._h_offset), self.font_size)
        self.password.bind('password')
        self.working_image().paste(password_image, (x,y))
        self.add(self.password, x + password_image.size[0], y)
        y += self._password_height + self._v_offset
        self.ok = Button('OK', 30, 20)
        self.ok.add_callback(self.check_password, 'on_button_press')
        self.add(self.ok, x, y)
        x = self.w/2 + self._h_offset
        self.cancel = Button('Cancel', 30, 20)
        self.ok.add_callback(self.cancel, 'on_button_press')
        self.add(self.cancel, x, y)
        

    def check_password(self, widget):
        self._value = widget.value
        self._done.set()

    def cancel(self, widget):
        self._done.set()

    def add_close_buttons(self):
        pass

    
