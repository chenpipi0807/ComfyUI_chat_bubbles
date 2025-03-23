import os
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont, ImageColor
import textwrap
import datetime
import json

class TextBubbleNode:
    """
    文本聊天气泡节点，用于创建聊天气泡效果
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        # 加载语言配置
        languages = cls._get_language_options()
        
        return {
            "required": {
                "文本内容": ("STRING", {"multiline": True, "default": "你好！这是一条测试消息。"}),
                "气泡样式": (["普通", "特殊一", "特殊二", "特殊三"], {"default": "普通"}),
                "气泡背景颜色": ("STRING", {"default": "#B19CD9"}),
                "文本颜色": ("STRING", {"default": "#000000"}),
                "发送者位置": (["右侧", "左侧"], {"default": "右侧"}),
                "显示尾巴": (["是", "否"], {"default": "是"}),
                "字体大小": ("INT", {"default": 24, "min": 10, "max": 80}),
                "气泡宽度": ("INT", {"default": 400, "min": 100, "max": 2000}),
                "内边距": ("INT", {"default": 20, "min": 5, "max": 100}),
                "图像分辨率": ("INT", {"default": 4, "min": 1, "max": 4, "step": 1}),
                "语言": (languages, {"default": "简体中文"}),
            },
        }
    
    @classmethod
    def _get_language_options(cls):
        """获取所有可用的语言选项"""
        # 配置文件路径
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "font_config.json")
        
        # 默认语言列表，以防配置文件不存在
        default_languages = ["简体中文", "English"]
        
        # 如果配置文件存在，从中读取语言列表
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return [lang["name"] for lang in config["languages"]]
            except Exception as e:
                print(f"无法加载语言配置文件: {e}")
                
        return default_languages
    
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "create_bubble"
    CATEGORY = "聊天气泡"
    
    def _prepare_color(self, color_str):
        """将各种颜色格式转换为RGBA元组"""
        # 默认颜色为白色
        default_color = (255, 255, 255, 255)
        
        if not color_str:
            return default_color
            
        try:
            # 如果是RGB、RGBA格式的元组或列表
            if isinstance(color_str, (tuple, list)):
                if len(color_str) == 3:
                    return color_str + (255,)  # 添加Alpha通道
                elif len(color_str) == 4:
                    return color_str
                else:
                    return default_color
            
            # 如果是以#开头的16进制颜色
            elif isinstance(color_str, str) and color_str.startswith('#'):
                try:
                    rgba = ImageColor.getrgb(color_str) + (255,) if len(ImageColor.getrgb(color_str)) == 3 else ImageColor.getrgb(color_str)
                    return rgba
                except ValueError:
                    return default_color
            
            # 如果是其他格式，转换失败则返回默认颜色
            else:
                return default_color
                
        except Exception as e:
            print(f"颜色转换错误: {e}")
            return default_color
    
    def _get_font_for_language(self, language):
        """根据选择的语言返回对应的字体文件路径"""
        # 配置文件路径
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "font_config.json")
        font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
        
        # 默认字体
        default_font = "NotoSansSC-Regular.ttf"
        
        # 如果配置文件存在，从中读取语言-字体映射
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                    # 寻找匹配的语言配置
                    for lang in config["languages"]:
                        if lang["name"] == language:
                            font_file = lang["font"]
                            font_path = os.path.join(font_dir, font_file)
                            
                            # 检查字体文件是否存在
                            if os.path.exists(font_path):
                                return font_path
                            else:
                                print(f"字体文件不存在: {font_path}，将使用系统字体")
                                break
                    
                    # 如果找不到匹配的语言，使用回退字体
                    fallback_font = config.get("fallback_font", default_font)
                    fallback_path = os.path.join(font_dir, fallback_font)
                    if os.path.exists(fallback_path):
                        return fallback_path
            except Exception as e:
                print(f"加载字体配置文件失败: {e}")
        
        # 如果无法从配置文件获取字体，使用系统字体
        if os.name == 'nt':  # Windows
            system_font = "C:\\Windows\\Fonts\\msyh.ttc"  # 微软雅黑
            if not os.path.exists(system_font):
                system_font = "C:\\Windows\\Fonts\\arial.ttf"
        elif os.name == 'posix':  # Linux/Mac
            system_font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            if not os.path.exists(system_font):
                system_font = "/System/Library/Fonts/Helvetica.ttc"  # Mac fallback
        else:
            system_font = None
            
        return system_font
    
    def create_bubble(self, 文本内容, 气泡样式, 气泡背景颜色, 文本颜色, 发送者位置, 显示尾巴, 字体大小, 气泡宽度, 内边距, 图像分辨率, 语言):
        # 根据分辨率因子调整尺寸
        字体大小 = 字体大小 * 图像分辨率
        气泡宽度 = 气泡宽度 * 图像分辨率
        内边距 = 内边距 * 图像分辨率
        
        # 添加额外边距以避免裁剪
        额外边距 = 10 * 图像分辨率
        
        # 获取与语言匹配的字体
        font_path = self._get_font_for_language(语言)
        
        # Determine style and colors
        is_sender = 发送者位置 == "右侧"
        show_tail = 显示尾巴 == "是"
        
        # 使用辅助方法处理颜色
        print(f"气泡背景颜色：{气泡背景颜色}")  # 调试信息
        color_rgba = self._prepare_color(气泡背景颜色)
        text_color_rgb = self._prepare_color(文本颜色)[:3]  # 文本颜色只需要RGB
        print(f"转换后的颜色 -> RGBA: {color_rgba}")
        
        # Create font object
        try:
            font = ImageFont.truetype(font_path, 字体大小)
            print(f"使用字体: {font_path} 显示{语言}文本")
        except (IOError, OSError) as e:
            print(f"加载字体失败: {e}，将使用默认字体")
            font = ImageFont.load_default()
        
        # Calculate text dimensions
        text_lines = textwrap.wrap(文本内容, width=int(气泡宽度 / (字体大小 * 0.6)))
        
        # Create a temporary image to measure text dimensions
        temp_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_img)
        
        # Calculate text dimensions
        text_height = 0
        text_width = 0
        
        for line in text_lines:
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            line_height = bbox[3] - bbox[1]
            text_height += line_height + 4  # Add a little extra spacing
            text_width = max(text_width, line_width)
        
        # Adjust for the last line's extra spacing
        text_height -= 4
        
        # Calculate bubble dimensions
        bubble_width = text_width + 内边距 * 2
        bubble_height = text_height + 内边距 * 2
        
        # Add extra width or height for tail if needed
        tail_width = 20 * 图像分辨率 if show_tail else 0
        tail_height = 20 * 图像分辨率 if show_tail else 0
        
        # 创建一个新的PIL图像，明确设置背景为透明，添加额外边距避免裁剪
        if not show_tail:
            img = Image.new('RGBA', (bubble_width + 额外边距 * 2, bubble_height + 额外边距 * 2), (0, 0, 0, 0))
        else:
            img = Image.new('RGBA', (bubble_width + tail_width + 额外边距 * 2, bubble_height + tail_height + 额外边距 * 2), (0, 0, 0, 0))
            
        # 在这里直接测试背景颜色是否有效 - 创建一个纯色测试图像
        test_color = color_rgba[:3] + (200,)  # 使用一定透明度，200表示部分透明
        test_img = Image.new('RGBA', (50, 50), test_color)
        
        # 将测试图像粘贴到主图像上
        img.paste(test_img, (额外边距 + 10, 额外边距 + 10), test_img)
        
        draw = ImageDraw.Draw(img)
        
        # Create the bubble shape based on style
        if 气泡样式 == "普通":
            # 普通样式 - 尾巴在对角位置
            self._draw_bubble(draw, color_rgba, bubble_width, bubble_height, is_sender, show_tail, 额外边距)
        
        elif 气泡样式 == "特殊一":
            # Special style 1 - Sharper corners
            self._draw_bubble_style1(draw, color_rgba, bubble_width, bubble_height, is_sender, show_tail, 额外边距)
        
        elif 气泡样式 == "特殊二":
            # Special style 2 - Very rounded
            self._draw_bubble_style2(draw, color_rgba, bubble_width, bubble_height, is_sender, show_tail, 额外边距)
        
        elif 气泡样式 == "特殊三":
            # Special style 3 - 类似于普通样式但位置不同
            self._draw_bubble_style3(draw, color_rgba, bubble_width, bubble_height, is_sender, show_tail, 额外边距)
        
        # Draw the text
        y_offset = 额外边距 + 内边距
        x_offset = 额外边距 + 内边距
        
        for line in text_lines:
            bbox = font.getbbox(line)
            line_height = bbox[3] - bbox[1]
            draw.text((x_offset, y_offset), line, fill=text_color_rgb, font=font)
            y_offset += line_height + 4
        
        # Convert PIL image to numpy array
        bubble_np = np.array(img).astype(np.float32) / 255.0
        
        # 额外调试 - 输出图像数组信息
        print(f"气泡图像形状: {bubble_np.shape}")
        print(f"气泡图像数据类型: {bubble_np.dtype}")
        print(f"气泡图像值范围: {np.min(bubble_np)} 到 {np.max(bubble_np)}")
        
        # 保持透明通道
        # 确保输出包含alpha通道
        if bubble_np.shape[2] == 4:
            # 创建包含RGB和Alpha的输出
            bubble_rgba = bubble_np.copy()  # 直接复制整个数组，保留原始颜色
            print(f"保持透明背景，气泡颜色为: {color_rgba[:3]}")
            print(f"输出图像是否有透明通道: 是")
        else:
            # 如果没有透明通道，确保创建一个
            print(f"图像没有透明通道，创建一个...")
            bubble_rgba = np.zeros((bubble_height + 额外边距 * 2, bubble_width + tail_width + 额外边距 * 2, 4), dtype=np.float32)
            bubble_rgba[:, :, :3] = bubble_np
            bubble_rgba[:, :, 3] = 1.0  # 完全不透明
            bubble_np = bubble_rgba
            
        # 打印最终输出数组的一些像素值作为调试
        sample_points = [(额外边距 + 10, 额外边距 + 10), (bubble_np.shape[0]//2, bubble_np.shape[1]//2)]
        for y, x in sample_points:
            if y < bubble_np.shape[0] and x < bubble_np.shape[1]:
                print(f"位置 ({y},{x}) 的颜色值: {bubble_np[y,x]}")
        
        # Convert numpy array to PyTorch tensor
        bubble_tensor = torch.from_numpy(bubble_np)[None,]
        
        return (bubble_tensor,)

    def _draw_bubble(self, draw, color, width, height, is_sender, show_tail, 额外边距=0):
        """画一个基本的圆角矩形气泡，尾巴在对角位置"""
        # 直接使用传入的颜色，color现在应该是RGBA格式
        print(f"绘制气泡使用的颜色: {color}")
        
        # Set radius and tail dimensions
        radius = 15
        tail_width = 40
        tail_height = 35
        
        # 计算位置，考虑额外边距
        left = 额外边距
        right = 额外边距 + width
        top = 额外边距
        bottom = 额外边距 + height
        
        # Draw the rounded rectangle
        draw.rectangle([(left + radius, top), (right - radius, bottom)], fill=color)
        draw.rectangle([(left, top + radius), (right, bottom - radius)], fill=color)
        
        # Draw the four corners
        draw.pieslice([(left, top), (left + radius * 2, top + radius * 2)], 180, 270, fill=color)
        draw.pieslice([(right - radius * 2, top), (right, top + radius * 2)], 270, 360, fill=color)
        draw.pieslice([(left, bottom - radius * 2), (left + radius * 2, bottom)], 90, 180, fill=color)
        draw.pieslice([(right - radius * 2, bottom - radius * 2), (right, bottom)], 0, 90, fill=color)
        
        # 只有在需要显示尾巴时才绘制
        if show_tail:
            # 根据发送者位置决定尾巴的位置
            if is_sender:
                # 尾巴在右下角，更尖锐的形状
                tail_points = [
                    (right - 15, bottom - 20),
                    (right + tail_width, bottom + tail_height),
                    (right - 60, bottom)
                ]
            else:
                # 尾巴在左下角，更尖锐的形状
                tail_points = [
                    (left + 15, bottom - 20),
                    (left - tail_width, bottom + tail_height),
                    (left + 60, bottom)
                ]
            
            # 绘制尾巴（三角形）
            draw.polygon(tail_points, fill=color)

    def _draw_bubble_style1(self, draw, color, width, height, is_sender, show_tail, 额外边距=0):
        """画一个带有尖角的气泡"""
        # 直接使用传入的颜色，color现在应该是RGBA格式
        print(f"绘制样式1气泡使用的颜色: {color}")
        
        # Set radius and tail dimensions (very rounded)
        radius = 8  # Sharper corners
        tail_width = 20
        tail_height = 15
        
        # Calculate positions
        if is_sender and show_tail:
            # Right side of bubble
            left = 额外边距
            right = 额外边距 + width
            top = 额外边距
            bottom = 额外边距 + height
            
            # Draw the rounded rectangle with sharper corners
            draw.rectangle([(left + radius, top), (right - radius, bottom)], fill=color)
            draw.rectangle([(left, top + radius), (right, bottom - radius)], fill=color)
            
            # Draw the four corners
            draw.pieslice([(left, top), (left + radius * 2, top + radius * 2)], 180, 270, fill=color)
            draw.pieslice([(right - radius * 2, top), (right, top + radius * 2)], 270, 360, fill=color)
            draw.pieslice([(left, bottom - radius * 2), (left + radius * 2, bottom)], 90, 180, fill=color)
            draw.pieslice([(right - radius * 2, bottom - radius * 2), (right, bottom)], 0, 90, fill=color)
            
            # Draw a sharp pointed tail on the right
            tail_points = [(right, bottom - height // 4),
                          (right + tail_width, bottom - height // 2),
                          (right, bottom - 3 * height // 4)]
            draw.polygon(tail_points, fill=color)
            
        elif not is_sender and show_tail:
            # Left side of bubble
            left = 额外边距 + tail_width
            right = 额外边距 + width + tail_width
            top = 额外边距
            bottom = 额外边距 + height
            
            # Draw the rounded rectangle
            draw.rectangle([(left + radius, top), (right - radius, bottom)], fill=color)
            draw.rectangle([(left, top + radius), (right, bottom - radius)], fill=color)
            
            # Draw the four corners
            draw.pieslice([(left, top), (left + radius * 2, top + radius * 2)], 180, 270, fill=color)
            draw.pieslice([(right - radius * 2, top), (right, top + radius * 2)], 270, 360, fill=color)
            draw.pieslice([(left, bottom - radius * 2), (left + radius * 2, bottom)], 90, 180, fill=color)
            draw.pieslice([(right - radius * 2, bottom - radius * 2), (right, bottom)], 0, 90, fill=color)
            
            # Draw a sharp pointed tail on the left
            tail_points = [(left, bottom - height // 4),
                          (left - tail_width, bottom - height // 2),
                          (left, bottom - 3 * height // 4)]
            draw.polygon(tail_points, fill=color)
        else:
            # No tail, just draw a rounded rectangle
            left = 额外边距 if is_sender else 额外边距 + tail_width
            right = 额外边距 + width if is_sender else 额外边距 + width + tail_width
            top = 额外边距
            bottom = 额外边距 + height
            
            # Draw the rounded rectangle
            draw.rectangle([(left + radius, top), (right - radius, bottom)], fill=color)
            draw.rectangle([(left, top + radius), (right, bottom - radius)], fill=color)
            
            # Draw the four corners
            draw.pieslice([(left, top), (left + radius * 2, top + radius * 2)], 180, 270, fill=color)
            draw.pieslice([(right - radius * 2, top), (right, top + radius * 2)], 270, 360, fill=color)
            draw.pieslice([(left, bottom - radius * 2), (left + radius * 2, bottom)], 90, 180, fill=color)
            draw.pieslice([(right - radius * 2, bottom - radius * 2), (right, bottom)], 0, 90, fill=color)

    def _draw_bubble_style2(self, draw, color, width, height, is_sender, show_tail, 额外边距=0):
        """画一个高度圆润的气泡"""
        # 直接使用传入的颜色，color现在应该是RGBA格式
        print(f"绘制样式2气泡使用的颜色: {color}")
        
        # Set radius and tail dimensions (very rounded)
        radius = min(25, height // 2 - 2)  # More rounded corners, but not exceeding half height
        tail_width = 25
        tail_height = 20
        
        # Calculate positions
        if is_sender and show_tail:
            # Right side of bubble
            left = 额外边距
            right = 额外边距 + width
            top = 额外边距
            bottom = 额外边距 + height
            
            # Draw the rounded rectangle with very rounded corners
            draw.rectangle([(left + radius, top), (right - radius, bottom)], fill=color)
            draw.rectangle([(left, top + radius), (right, bottom - radius)], fill=color)
            
            # Draw the four corners
            draw.pieslice([(left, top), (left + radius * 2, top + radius * 2)], 180, 270, fill=color)
            draw.pieslice([(right - radius * 2, top), (right, top + radius * 2)], 270, 360, fill=color)
            draw.pieslice([(left, bottom - radius * 2), (left + radius * 2, bottom)], 90, 180, fill=color)
            draw.pieslice([(right - radius * 2, bottom - radius * 2), (right, bottom)], 0, 90, fill=color)
            
            # Draw a smooth curved tail on the right
            # Create a smoother curve with additional points
            tail_start = (right, bottom - height // 3)
            tail_end = (right, bottom - 2 * height // 3)
            tail_mid = (right + tail_width, bottom - height // 2)
            
            # Draw a series of points to create a smooth curve
            points = [tail_start]
            for i in range(1, 9):
                t = i / 10
                x = (1-t)**2 * tail_start[0] + 2*(1-t)*t*tail_mid[0] + t**2*tail_end[0]
                y = (1-t)**2 * tail_start[1] + 2*(1-t)*t*tail_mid[1] + t**2*tail_end[1]
                points.append((x, y))
            points.append(tail_end)
            
            draw.polygon(points, fill=color)
            
        elif not is_sender and show_tail:
            # Left side of bubble
            left = 额外边距 + tail_width
            right = 额外边距 + width + tail_width
            top = 额外边距
            bottom = 额外边距 + height
            
            # Draw the rounded rectangle
            draw.rectangle([(left + radius, top), (right - radius, bottom)], fill=color)
            draw.rectangle([(left, top + radius), (right, bottom - radius)], fill=color)
            
            # Draw the four corners
            draw.pieslice([(left, top), (left + radius * 2, top + radius * 2)], 180, 270, fill=color)
            draw.pieslice([(right - radius * 2, top), (right, top + radius * 2)], 270, 360, fill=color)
            draw.pieslice([(left, bottom - radius * 2), (left + radius * 2, bottom)], 90, 180, fill=color)
            draw.pieslice([(right - radius * 2, bottom - radius * 2), (right, bottom)], 0, 90, fill=color)
            
            # Draw a smooth curved tail on the left
            tail_start = (left, bottom - height // 3)
            tail_end = (left, bottom - 2 * height // 3)
            tail_mid = (left - tail_width, bottom - height // 2)
            
            # Draw a series of points to create a smooth curve
            points = [tail_start]
            for i in range(1, 9):
                t = i / 10
                x = (1-t)**2 * tail_start[0] + 2*(1-t)*t*tail_mid[0] + t**2*tail_end[0]
                y = (1-t)**2 * tail_start[1] + 2*(1-t)*t*tail_mid[1] + t**2*tail_end[1]
                points.append((x, y))
            points.append(tail_end)
            
            draw.polygon(points, fill=color)
        else:
            # No tail, just draw a very rounded rectangle
            left = 额外边距 if is_sender else 额外边距 + tail_width
            right = 额外边距 + width if is_sender else 额外边距 + width + tail_width
            top = 额外边距
            bottom = 额外边距 + height
            
            # Draw the rounded rectangle
            draw.rectangle([(left + radius, top), (right - radius, bottom)], fill=color)
            draw.rectangle([(left, top + radius), (right, bottom - radius)], fill=color)
            
            # Draw the four corners
            draw.pieslice([(left, top), (left + radius * 2, top + radius * 2)], 180, 270, fill=color)
            draw.pieslice([(right - radius * 2, top), (right, top + radius * 2)], 270, 360, fill=color)
            draw.pieslice([(left, bottom - radius * 2), (left + radius * 2, bottom)], 90, 180, fill=color)
            draw.pieslice([(right - radius * 2, bottom - radius * 2), (right, bottom)], 0, 90, fill=color)

    def _draw_bubble_style3(self, draw, color, width, height, is_sender, show_tail, 额外边距=0):
        """画一个类似于普通气泡的样式，但尾巴位置不同"""
        # 直接使用传入的颜色，color现在应该是RGBA格式
        print(f"绘制样式3气泡使用的颜色: {color}")
        
        # Set radius and tail dimensions
        radius = 15
        tail_width = 20
        tail_height = 15
        
        # 计算位置，考虑额外边距
        if is_sender and show_tail:
            # Right side of bubble
            left = 额外边距
            right = 额外边距 + width
            top = 额外边距
            bottom = 额外边距 + height
            
            # Draw the rounded rectangle
            draw.rectangle([(left + radius, top), (right - radius, bottom)], fill=color)
            draw.rectangle([(left, top + radius), (right, bottom - radius)], fill=color)
            
            # Draw the four corners
            draw.pieslice([(left, top), (left + radius * 2, top + radius * 2)], 180, 270, fill=color)
            draw.pieslice([(right - radius * 2, top), (right, top + radius * 2)], 270, 360, fill=color)
            draw.pieslice([(left, bottom - radius * 2), (left + radius * 2, bottom)], 90, 180, fill=color)
            draw.pieslice([(right - radius * 2, bottom - radius * 2), (right, bottom)], 0, 90, fill=color)
            
            # Draw the tail (a triangle) on the right side
            tail_points = [(right, bottom - height // 3),
                          (right + tail_width, bottom - height // 2),
                          (right, bottom - 2 * height // 3)]
            draw.polygon(tail_points, fill=color)
            
        elif not is_sender and show_tail:
            # Left side of bubble
            left = 额外边距 + tail_width
            right = 额外边距 + width + tail_width
            top = 额外边距
            bottom = 额外边距 + height
            
            # Draw the rounded rectangle
            draw.rectangle([(left + radius, top), (right - radius, bottom)], fill=color)
            draw.rectangle([(left, top + radius), (right, bottom - radius)], fill=color)
            
            # Draw the four corners
            draw.pieslice([(left, top), (left + radius * 2, top + radius * 2)], 180, 270, fill=color)
            draw.pieslice([(right - radius * 2, top), (right, top + radius * 2)], 270, 360, fill=color)
            draw.pieslice([(left, bottom - radius * 2), (left + radius * 2, bottom)], 90, 180, fill=color)
            draw.pieslice([(right - radius * 2, bottom - radius * 2), (right, bottom)], 0, 90, fill=color)
            
            # Draw the tail (a triangle) on the left side
            tail_points = [(left, bottom - height // 3),
                          (left - tail_width, bottom - height // 2),
                          (left, bottom - 2 * height // 3)]
            draw.polygon(tail_points, fill=color)
        else:
            # No tail, just draw a rounded rectangle
            left = 额外边距 if is_sender else 额外边距 + tail_width
            right = 额外边距 + width if is_sender else 额外边距 + width + tail_width
            top = 额外边距
            bottom = 额外边距 + height
            
            # Draw the rounded rectangle
            draw.rectangle([(left + radius, top), (right - radius, bottom)], fill=color)
            draw.rectangle([(left, top + radius), (right, bottom - radius)], fill=color)
            
            # Draw the four corners
            draw.pieslice([(left, top), (left + radius * 2, top + radius * 2)], 180, 270, fill=color)
            draw.pieslice([(right - radius * 2, top), (right, top + radius * 2)], 270, 360, fill=color)
            draw.pieslice([(left, bottom - radius * 2), (left + radius * 2, bottom)], 90, 180, fill=color)
            draw.pieslice([(right - radius * 2, bottom - radius * 2), (right, bottom)], 0, 90, fill=color)

# 节点映射
NODE_CLASS_MAPPINGS = {
    "文本聊天气泡": TextBubbleNode,
    "TextBubble": TextBubbleNode
}

# 节点显示名称
NODE_DISPLAY_NAME_MAPPINGS = {
    "文本聊天气泡": "文本聊天气泡",
    "TextBubble": "Text Chat Bubble"
}
