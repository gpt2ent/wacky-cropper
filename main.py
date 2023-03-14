import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox

import os, time
from PIL import Image, ImageTk

TARGET_SIZE = 512


def rescale_to_fit(image, dx=0, dy=0, scale=1, minsize=TARGET_SIZE, bgcolor=(0,0,0)):
    smallsize, bigsize = sorted(image.size)
    scale_factor = minsize/smallsize * scale

    resized = image.resize((int(image.width*scale_factor), int(image.height*scale_factor)))

    x1 = int(dx*scale+minsize/2*scale-minsize/2)
    y1 = int(dy*scale+minsize/2*scale-minsize/2)

    x2, y2 = int(x1+minsize), int(y1+minsize)
    cropped = Image.new('RGB', (x2 - x1, y2 - y1), bgcolor)
    cropped.paste(resized, (-x1, -y1))

    return cropped

def suggest_dx(image, minsize=TARGET_SIZE):
    if image.width <= image.height: return 0
    newwidth = image.width/image.height*minsize
    return int(0.5*(newwidth-minsize))


class ZoomableImageHolder:
    def __init__(self):
        self.raw_image = None
        self.processed_image = None
        self.dx = 0
        self.dy = 0
        self.scale = 1
        self.bg = (0,0,0)

    def new(self, image_path):
        self.raw_image = Image.open(image_path)
        self.processed_image = rescale_to_fit(self.raw_image)
        self.dx = suggest_dx(self.raw_image)
        self.dy = 0
        self.scale = 1
        self.bg = (0,0,0)
        self.processed_tk = ImageTk.PhotoImage(self.processed_image)

    def upd(self, newdx=None, newdy=None, newscale=None, newbg=None):
        if newdx is not None:
            self.dx = newdx
        if newdy is not None:
            self.dy = newdy
        if newscale is not None:
            self.scale = newscale

        if newbg is not None:
            self.bg = newbg

        self.processed_image = rescale_to_fit(self.raw_image,
                                              self.dx,
                                              self.dy,
                                              self.scale,
                                              bgcolor=self.bg)

        self.processed_tk = ImageTk.PhotoImage(self.processed_image)

    def get(self):
        return self.processed_image

    def get_tk(self):
        return self.processed_tk

class Logic:
    def __init__(self, in_folder, out_folder):
        self.in_folder = in_folder
        self.out_folder = out_folder
        self.list = [os.path.join(in_folder, fname) for fname in os.listdir(in_folder) if fname.endswith('.jpg') or fname.endswith('.png') or fname.endswith('.bmp')]
        if len(self.list) < 1:
            raise OSError(f"{in_folder} does not contain images")

        self.current_index = 0
        self.has_reached_end = False

        self.img = ZoomableImageHolder()
        self.img.new(self.list[0])

    def get(self):
        return self.img.get()

    def get_tk(self):
        return self.img.get_tk()

    def upd(self, *args, **kwargs):
        return self.img.upd(*args, **kwargs)

    def snap(self):
        i = self.get()
        fname = str(time.time()).replace('.','-')+'.png'
        i.save(os.path.join(self.out_folder, fname))
        return fname

    def progress(self):
        self.current_index += 1
        if self.current_index >= len(self.list):
            self.has_reached_end = True
            self.img = None
        else:
            self.img.new(self.list[self.current_index])

    def goback(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.img.new(self.list[self.current_index])

    def goindex(self, index):
        if 0 <= index < len(self.list):
            self.current_index = index
            self.img.new(self.list[self.current_index])

class Application(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)

        self.drag_x = None
        self.drag_y = None
        self.init_x = None
        self.init_y = None
        self.logic_attached = False
        self.in_folder = None
        self.out_folder = None
        self.bg = (0,0,0)
        self.grid()
        self.createWidgets()

    def attach_logic(self):
        try:
            self.logic = Logic(self.in_folder, self.out_folder)
            self.logic_attached = True
            self.show_new()
        except OSError:
            messagebox.showerror("Error parsing folder", f"{self.in_folder} doesn't contain images!")

    def detach_logic(self):
        self.logic = None
        self.canvas.delete("all")
        self.logic_attached = False

    def show_new(self):
        self.canvas.delete("all")
        self.logic.upd(newbg=self.bg)
        self.canvas.create_image(0, 0, image=self.logic.get_tk(), anchor=tk.NW)
        self.info_label['text'] = f'{self.logic.current_index+1}/{len(self.logic.list)}'
        self.info_label['text'] += '\n' + self.logic.list[self.logic.current_index]

    def createWidgets(self):
        self.filter_criteria = tk.Entry()
        self.filter_criteria.insert(0,"write yourself a memo")
        self.filter_criteria.grid(row=1,column=0,columnspan=2)
        self.info_label = tk.Label(text='...')
        self.info_label.grid(row=2,column=0,columnspan=3)
        self.canvas = tk.Canvas(width=TARGET_SIZE, height=TARGET_SIZE)
        self.canvas.grid(row=3,column=0,columnspan=3)
        self.canvas.bind("<ButtonRelease-1>", self.stopdrag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)
        self.canvas.bind("<Button-2>", self.resetimg)

        self.return_button = tk.Button(text="<<")
        self.return_button.bind('<Button-1>', self.ret)
        self.snap_button = tk.Button(text="Snap!")
        self.snap_button.bind('<Button-1>', self.snap)
        self.next_button = tk.Button(text=">>")
        self.next_button.bind('<Button-1>', self.next)

        self.return_button.grid(row=4,column=0)
        self.snap_button.grid(row=4,column=1)
        self.next_button.grid(row=4,column=2)

        self.open_folder_button = tk.Button(text="Input folder...")
        self.save_folder_button = tk.Button(text="Output folder...")
        self.open_folder_button.bind('<Button-1>', self.get_in_folder)
        self.save_folder_button.bind('<Button-1>', self.get_out_folder)
        self.open_folder_button.grid(row=0, column=0)
        self.save_folder_button.grid(row=0, column=1)
        self.pick_color_button = tk.Button(text="Pick background color...")
        self.pick_color_button.bind("<Button-1>", self.pick_color)
        self.pick_color_button.grid(row=0, column=2)

        self.snap_label = tk.Label(text="")
        self.snap_label.grid(row=5, column=0, columnspan=3)

        self.bind('<KeyRelease-space>',self.next)
        self.bind('<KeyRelease-s>',self.snap)
        self.bind('<KeyRelease-q>',self.ret)

        self.goto_index_button = tk.Button(text="Go to index")
        self.goto_index_entry = tk.Entry()
        self.goto_index_button.grid(row=6,column=0)
        self.goto_index_entry.grid(row=6,column=1)
        self.goto_index_button.bind("<Button-1>", self.goto_index)

    def goto_index(self, _):
        if not self.logic_attached: return
        try:
            index = self.goto_index_entry.get()
            index = int(index)-1
            self.logic.goindex(index)
            self.show_new()
        except ValueError:
            print('index not found, ignored',self.goto_index_entry.get())
        self.after(20, self.focus_set)

    def pick_color(self, _):
        if not self.logic_attached: return
        newbg = colorchooser.askcolor()
        print(newbg)
        if newbg is not None:
            newbg = tuple([int(x) for x in newbg[0]])
            self.bg = newbg
            self.logic.upd(newbg=newbg)
            self.show_new()
        self.after(20, self.focus_set)
        return "break"

    def get_in_folder(self, _):
        self.in_folder = filedialog.askdirectory()
        if self.in_folder is not None and self.out_folder is not None:
            self.attach_logic()
        self.after(20, self.focus_set)
        return "break"

    def get_out_folder(self, _):
        self.out_folder = filedialog.askdirectory()
        if self.in_folder is not None and self.out_folder is not None:
            self.attach_logic()
        self.after(20, self.focus_set)
        return "break"

    def stopdrag(self, _):
        self.drag_x = self.drag_y = None
        self.init_x = self.init_y = None
        self.focus_set()

    def resetimg(self, _):
        if not self.logic_attached: return
        self.logic.upd(suggest_dx(self.logic.img.raw_image), 0, 1)
        self.show_new()
        self.after(20, self.focus_set)

    def _on_mousewheel(self, event):
        if not self.logic_attached: return
        scale = self.logic.img.scale
        if event.num == 4 or event.delta == 120:
            newscale = scale*1.1
        elif event.num == 5 or event.delta == -120:
            newscale = scale/1.1
        self.logic.upd(newscale=newscale)
        self.show_new()
        self.focus_set()

    def ret(self, _):
        if not self.logic_attached: return
        self.logic.goback()
        self.show_new()
        self.after(20, self.focus_set)

    def next(self, _):
        if not self.logic_attached: return
        self.logic.progress()
        if not self.logic.has_reached_end:
            self.show_new()
        else:
            self.detach_logic()
            self.info_label['text'] = f'Reached end of the folder! Reopen it to start anew!'
        self.after(20, self.focus_set)

    def snap(self, _):
        if not self.logic_attached: return
        fname = self.logic.snap()
        self.snap_label['text'] = f'{fname} just saved'
        self.after(2000, self.clear_snap_label)
        self.after(20, self.focus_set)

    def clear_snap_label(self):
        self.snap_label['text'] = ''

    def drag(self, event):
        if self.drag_x is None:
            self.drag_x = event.x
            self.init_x = self.logic.img.dx
            self.drag_y = event.y
            self.init_y = self.logic.img.dy
        else:
            dx = (self.drag_x - event.x)/self.logic.img.scale + self.init_x
            dy = (self.drag_y - event.y)/self.logic.img.scale + self.init_y
            self.logic.upd(newdx=int(dx), newdy=int(dy))
            self.show_new()



app = Application()
app.master.title('Wacky Cropper 🥴')
app.mainloop()
