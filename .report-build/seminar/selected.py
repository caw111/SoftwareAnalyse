from pypdf import PdfReader
r=PdfReader('E:/weichat/xwechat_files/wxid_quoop5hprm8122_9298/msg/file/2026-11/ssad05.架构设计.pdf')
for i in [27,28,29,57,58,59,64,65,66,67]: print('\nPDF PAGE',i+1,'\n',r.pages[i].extract_text())
