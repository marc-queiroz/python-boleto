# -*- coding: utf-8 -*-
"""
    pyboleto.pdf
    ~~~~~~~~~~~~

    Classe Responsável por fazer o output do boleto em pdf usando Reportlab.

    :copyright: © 2011 - 2012 by Eduardo Cereto Carvalho
    :license: BSD, see LICENSE for more details.

"""
import base64
import io
import locale
import os

from reportlab.graphics.barcode.common import I2of5
from reportlab.lib.colors import black
from reportlab.lib.pagesizes import A4, landscape as pagesize_landscape
from reportlab.lib.units import mm, cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image


class BoletoPDF(object):
    """Geração do Boleto em PDF

    Esta classe é responsável por imprimir o boleto em PDF.
    Outras classes podem ser implementadas no futuro com a mesma interface,
    para fazer output em HTML, LaTeX, ...

    Esta classe pode imprimir boletos em formato de carnê (2 boletos por
    página) ou em formato de folha cheia.

    :param file_descr: Um arquivo ou *file-like* class.
    :param landscape: Formato da folha. Usar ``True`` para boleto
        tipo carnê.

    """
    # pylint: disable=too-many-instance-attributes

    def __init__(self, file_descr, landscape=False):
        self.width = 190 * mm
        self.width_canhoto = 70 * mm
        self.height_line = 6.5 * mm
        self.space = 2
        self.font_size_title = 6
        self.font_size_value = 8
        self.delta_title = self.height_line - (self.font_size_title + 1)
        self.delta_font = self.font_size_value + 1

        if landscape:
            pagesize = pagesize_landscape(A4)
        else:
            pagesize = A4

        self.pdf_canvas = canvas.Canvas(file_descr, pagesize=pagesize)
        self.pdf_canvas.setStrokeColor(black)

    def _draw_recibo_sacado_canhoto(self, boleto_dados, x, y):
        """Imprime o Recibo do Sacado para modelo de carnê

        :param boleto_dados: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :type boleto_dados: :class:`pyboleto.data.BoletoData`
        :param x: Current X coordinate
        :param y: Current Y coordinate

        """

        self.pdf_canvas.saveState()
        self.pdf_canvas.translate(x, y)

        linha_inicial = 12

        # Horizontal Lines
        self.pdf_canvas.setLineWidth(2)
        self.__horizontalLine(0, 0, self.width_canhoto)

        self.pdf_canvas.setLineWidth(1)
        self.__horizontalLine(0,
                              (linha_inicial + 0) * self.height_line,
                              self.width_canhoto)
        self.__horizontalLine(0,
                              (linha_inicial + 1) * self.height_line,
                              self.width_canhoto)

        self.pdf_canvas.setLineWidth(2)
        self.__horizontalLine(0,
                              (linha_inicial + 2) * self.height_line,
                              self.width_canhoto)

        # Vertical Lines
        self.pdf_canvas.setLineWidth(1)
        self.__verticalLine(self.width_canhoto - (35 * mm),
                            (linha_inicial + 0) * self.height_line,
                            self.height_line)
        self.__verticalLine(self.width_canhoto - (35 * mm),
                            (linha_inicial + 1) * self.height_line,
                            self.height_line)

        self.pdf_canvas.setFont('Helvetica-Bold', 6)
        self.pdf_canvas.drawRightString(self.width_canhoto,
                                        0 * self.height_line + 3,
                                        'Recibo do Pagador')

        # Titles
        self.pdf_canvas.setFont('Helvetica', 6)
        self.delta_title = self.height_line - (6 + 1)

        self.pdf_canvas.drawString(
            self.space,
            (((linha_inicial + 0) * self.height_line)) + self.delta_title,
            'Nosso Número'
        )
        self.pdf_canvas.drawString(
            self.width_canhoto - (35 * mm) + self.space,
            (((linha_inicial + 0) * self.height_line)) + self.delta_title,
            'Vencimento'
        )
        self.pdf_canvas.drawString(
            self.space,
            (((linha_inicial + 1) * self.height_line)) + self.delta_title,
            'Agência/Código Beneficiário'
        )
        self.pdf_canvas.drawString(
            self.width_canhoto - (35 * mm) + self.space,
            (((linha_inicial + 1) * self.height_line)) + self.delta_title,
            'Valor Documento'
        )

        # Values
        self.pdf_canvas.setFont('Helvetica', 9)
        heigh_font = 9 + 1

        valor_documento = self._formataValorParaExibir(
            boleto_dados.valor_documento
        )

        self.pdf_canvas.drawString(
            self.space,
            (((linha_inicial + 0) * self.height_line)) + self.space,
            boleto_dados.format_nosso_numero()
        )
        self.pdf_canvas.drawString(
            self.width_canhoto - (35 * mm) + self.space,
            (((linha_inicial + 0) * self.height_line)) + self.space,
            boleto_dados.data_vencimento.strftime('%d/%m/%Y')
        )
        self.pdf_canvas.drawString(
            self.space,
            (((linha_inicial + 1) * self.height_line)) + self.space,
            boleto_dados.agencia_conta_cedente
        )
        self.pdf_canvas.drawString(
            self.width_canhoto - (35 * mm) + self.space,
            (((linha_inicial + 1) * self.height_line)) + self.space,
            valor_documento
        )

        demonstrativo = boleto_dados.demonstrativo[0:12]
        for index, value in enumerate(demonstrativo):
            self.pdf_canvas.drawString(
                2 * self.space,
                (linha_inicial - 1) * self.height_line - (index * heigh_font),
                value[0:55]
            )

        self.pdf_canvas.restoreState()

        return (self.width_canhoto,
                ((linha_inicial + 2) * self.height_line))

    def _drawReciboSacado(self, boleto_dados, x, y):
        """Imprime o Recibo do Sacado para modelo de página inteira

        :param boleto_dados: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :type boleto_dados: :class:`pyboleto.data.BoletoData`

        """

        self.pdf_canvas.saveState()
        self.pdf_canvas.translate(x, y)

        linha_inicial = 15

        # Horizontal Lines
        self.pdf_canvas.setLineWidth(1)
        self.__horizontalLine(0,
                              (linha_inicial + 0) * self.height_line,
                              self.width)
        self.__horizontalLine(0,
                              (linha_inicial + 1) * self.height_line,
                              self.width)
        self.__horizontalLine(0,
                              (linha_inicial + 2) * self.height_line,
                              self.width)

        self.pdf_canvas.setLineWidth(2)
        self.__horizontalLine(0,
                              (linha_inicial + 3) * self.height_line,
                              self.width)

        # Vertical Lines
        self.pdf_canvas.setLineWidth(1)
        self.__verticalLine(
            self.width - (30 * mm),
            (linha_inicial + 0) * self.height_line,
            3 * self.height_line
        )
        self.__verticalLine(
            self.width - (30 * mm) - (35 * mm),
            (linha_inicial + 1) * self.height_line,
            2 * self.height_line
        )
        self.__verticalLine(
            self.width - (30 * mm) - (35 * mm) - (40 * mm),
            (linha_inicial + 1) * self.height_line,
            2 * self.height_line
        )

        # Head
        self.pdf_canvas.setLineWidth(2)
        self.__verticalLine(40 * mm,
                            (linha_inicial + 3) * self.height_line,
                            self.height_line)
        self.__verticalLine(60 * mm,
                            (linha_inicial + 3) * self.height_line,
                            self.height_line)

        if boleto_dados.logo_image:
            image_reportlab = load_image(boleto_dados.logo_image)
            self.pdf_canvas.drawImage(
                image_reportlab,
                0, (linha_inicial + 3) * self.height_line + 3,
                40 * mm,
                self.height_line,
                preserveAspectRatio=True,
                anchor='sw'
            )
        self.pdf_canvas.setFont('Helvetica-Bold', 18)
        self.pdf_canvas.drawCentredString(
            50 * mm,
            (linha_inicial + 3) * self.height_line + 3,
            boleto_dados.codigo_dv_banco
        )
        self.pdf_canvas.setFont('Helvetica-Bold', 11.5)
        self.pdf_canvas.drawRightString(
            self.width,
            (linha_inicial + 3) * self.height_line + 3,
            'Recibo do Pagador'
        )

        # Titles
        self.pdf_canvas.setFont('Helvetica', 6)
        self.delta_title = self.height_line - (6 + 1)

        self.pdf_canvas.drawRightString(
            self.width,
            self.height_line,
            'Autenticação Mecânica'
        )

        self.pdf_canvas.drawString(
            0,
            (((linha_inicial + 2) * self.height_line)) + self.delta_title,
            'Beneficiário'
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) - (35 * mm) - (40 * mm) + self.space,
            (((linha_inicial + 2) * self.height_line)) + self.delta_title,
            'Agência/Código Beneficiário'
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) - (35 * mm) + self.space,
            (((linha_inicial + 2) * self.height_line)) + self.delta_title,
            'CPF/CNPJ Beneficiário'
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) + self.space,
            (((linha_inicial + 2) * self.height_line)) + self.delta_title,
            'Vencimento'
        )

        self.pdf_canvas.drawString(
            0,
            (((linha_inicial + 1) * self.height_line)) + self.delta_title,
            'Pagador')
        self.pdf_canvas.drawString(
            self.width - (30 * mm) - (35 * mm) - (40 * mm) + self.space,
            (((linha_inicial + 1) * self.height_line)) + self.delta_title,
            'Nosso Número')
        self.pdf_canvas.drawString(
            self.width - (30 * mm) - (35 * mm) + self.space,
            (((linha_inicial + 1) * self.height_line)) + self.delta_title,
            'N. do documento')
        self.pdf_canvas.drawString(
            self.width - (30 * mm) + self.space,
            (((linha_inicial + 1) * self.height_line)) + self.delta_title,
            'Data Documento'
        )

        self.pdf_canvas.drawString(
            0,
            (((linha_inicial + 0) * self.height_line)) + self.delta_title,
            'Endereço Beneficiário'
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) + self.space,
            (((linha_inicial + 0) * self.height_line)) + self.delta_title,
            'Valor Documento'
        )

        self.pdf_canvas.drawString(
            0,
            (((linha_inicial + 0) * self.height_line - 3 * cm)) +
            self.delta_title,
            'Demonstrativo'
        )

        # Values
        self.pdf_canvas.setFont('Helvetica', 8)
        heigh_font = 9 + 1

        cedente = boleto_dados.cedente
        self.pdf_canvas.drawString(
            0 + self.space,
            (((linha_inicial + 2) * self.height_line)) + self.space,
            cedente[:44] + ('...' if len(cedente) > 44 else '')
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) - (35 * mm) - (40 * mm) + self.space,
            (((linha_inicial + 2) * self.height_line)) + self.space,
            boleto_dados.agencia_conta_cedente
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) - (35 * mm) + self.space,
            (((linha_inicial + 2) * self.height_line)) + self.space,
            boleto_dados.cedente_documento
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) + self.space,
            (((linha_inicial + 2) * self.height_line)) + self.space,
            boleto_dados.data_vencimento.strftime('%d/%m/%Y')
        )

        # Take care of long field
        sacado0 = boleto_dados.sacado[0]
        while (stringWidth(sacado0,
                           self.pdf_canvas._fontname,
                           self.pdf_canvas._fontsize
                           ) > 8.4 * cm):

            # sacado0 = sacado0[:-2] + u'\u2026'
            sacado0 = sacado0[:-4] + '...'

        self.pdf_canvas.drawString(
            0 + self.space,
            (((linha_inicial + 1) * self.height_line)) + self.space,
            sacado0
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) - (35 * mm) - (40 * mm) + self.space,
            (((linha_inicial + 1) * self.height_line)) + self.space,
            boleto_dados.format_nosso_numero()
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) - (35 * mm) + self.space,
            (((linha_inicial + 1) * self.height_line)) + self.space,
            boleto_dados.numero_documento
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) + self.space,
            (((linha_inicial + 1) * self.height_line)) + self.space,
            boleto_dados.data_documento.strftime('%d/%m/%Y')
        )

        valor_documento = self._formataValorParaExibir(
            boleto_dados.valor_documento
        )

        self.pdf_canvas.drawString(
            0 + self.space,
            (((linha_inicial + 0) * self.height_line)) + self.space,
            boleto_dados.cedente_endereco
        )
        self.pdf_canvas.drawString(
            self.width - (30 * mm) + self.space,
            (((linha_inicial + 0) * self.height_line)) + self.space,
            valor_documento
        )

        self.pdf_canvas.setFont('Courier', 9)
        demonstrativo = boleto_dados.demonstrativo[0:25]
        for i in range(len(demonstrativo)):
            self.pdf_canvas.drawString(
                2 * self.space,
                (-3 * cm + ((linha_inicial + 0) * self.height_line)) -
                (i * heigh_font),
                demonstrativo[i])

        if boleto_dados.logo_image:
            base64image = "iVBORw0KGgoAAAANSUhEUgAAAPoAAAD6AQAAAACgl2eQAAAC1klEQVR4Xu2XS47rIBBFYSNm/7vopcBG4J1TRG0ng9YbtKsnrkSKDSfSTX0uTlk/x1f5XPmIB9jxADseYMf/Ab2UOusaax5ttll8DxcTgcF79CpZxzxKW9y5mAl014mGSpa9rZtJBUYnR4pckaij/QFAkhoMFfLGLCUDvFmcbrJx1OVnrKcB9uf4jM+u/tz/ZcCYCCRXJKwNqkbj7MgCemQo6sMlI1wonD2cCKjMSjk10bm4CFJTgd62ToYHmS1umZ6zaRMAlJEct6pJimzBqDENYFR6gQipxRQBL4cpD7Bcs+3jBA+jVi6N+MgCwjqax5py27Jox3uxbgc8xzxVD9dH2NewWJkAy9wyK3qXpwl1A7lW83bAVNVIThSset92rdIAvHPQr/TqcICGJgLIwZIH2J8+YGBj6NzJIg5VZgEIZNHkYOdMDmIt1KWa9wMjBqbooGhV3bR/r7/idoBeYZXnXkgu1BjCz19xP2B6Op3SXRsv97CNEgHSNLZ796jacpDGuPyK+4HpWdL0kCPUwiryLFYCYNtao31h93b6p+qoeQBNq4kTtCqdgmTH2W9kAUxtt2d1U8zE+SXon0SANaZVA5lyCNXRPO/zACpUHZ5ptnw5P1Tqu1gJAMOitBJOFpOMmzXxPMDjnP6IfXbsHr9yHd7bAded3kNh1IsHL2t3PdRuB+JER1ZRo1t8vNwsDRj7dG9LR53Uiz/F79XMAFhdkSJONdA9upfhvR9YkSsyBFg0khavs1gJwHRumtZVI01LT8NVzmomADZKMU0y3TFC9XEReT+gZSCKRFGrEikLX/sWmQAYeJcmXuNoVfH74X47oCL2lUW8PFVDTwRsET88WkmZeVOkGvMASoXQ4tD6XyhsXd3JgBliZlBGwlYk7yxWEsBC6z7eQHm4MDru5wG80ee04qNc6mGhOQ+IyrCL0ub0eCVswrKAn+IBdjzAjgfY8QvAP6fWH62SBojlAAAAAElFTkSuQmCC"
            image_bytes = base64.b64decode(base64image)
            image = Image.open(io.BytesIO(image_bytes))
            image_reportlab = ImageReader(image)
            self.pdf_canvas.drawImage(
                image_reportlab,
                0,
                (-3 * cm + ((linha_inicial + 0) * self.height_line)) -
                (len(demonstrativo) * heigh_font) - 36 * mm,
                36 * mm,
                36 * mm,
                preserveAspectRatio=True,
                anchor='sw'
            )

            self.pdf_canvas.drawString(36 * mm + self.space,
                (-3 * cm + ((linha_inicial + 0) * self.height_line)) -
                (len(demonstrativo) * heigh_font) - 6 * mm,
                'Para realizar o pagamento a qualquer instante, leia o QR Code'
            )

            self.pdf_canvas.drawString(36 * mm + self.space,
                (-3 * cm + ((linha_inicial + 0) * self.height_line)) -
                (heigh_font * (len(demonstrativo) + 1)) - 6 * mm,
                'no celular e pague por Pix.'
            )

        self.pdf_canvas.setFont('Helvetica', 9)

        self.pdf_canvas.restoreState()

        return (self.width, ((linha_inicial + 3) * self.height_line))

    def _drawHorizontalCorteLine(self, x, y, width):
        self.pdf_canvas.saveState()
        self.pdf_canvas.translate(x, y)

        self.pdf_canvas.setLineWidth(1)
        self.pdf_canvas.setDash(1, 2)
        self.__horizontalLine(0, 0, width)

        self.pdf_canvas.restoreState()

    def _drawVerticalCorteLine(self, x, y, height):
        self.pdf_canvas.saveState()
        self.pdf_canvas.translate(x, y)

        self.pdf_canvas.setLineWidth(1)
        self.pdf_canvas.setDash(1, 2)
        self.__verticalLine(0, 0, height)

        self.pdf_canvas.restoreState()

    def _drawReciboCaixa(self, boleto_dados, x, y):
        """Imprime o Recibo do Caixa

        :param boleto_dados: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :type boleto_dados: :class:`pyboleto.data.BoletoData`

        """
        self.pdf_canvas.saveState()

        self.pdf_canvas.translate(x, y)

        # De baixo para cima posicao 0,0 esta no canto inferior esquerdo
        self.pdf_canvas.setFont('Helvetica', self.font_size_title)

        y = 1.5 * self.height_line
        self.pdf_canvas.drawRightString(
            self.width,
            (1.5 * self.height_line) + self.delta_title - 1,
            'Autenticação Mecânica / Ficha de Compensação'
        )

        # Primeira linha depois do codigo de barra
        y += self.height_line
        self.pdf_canvas.setLineWidth(2)
        self.__horizontalLine(0, y, self.width)
        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.space, 'Código de baixa'
        )
        self.pdf_canvas.drawString(0, y + self.space, 'Sacador / Avalista')

        y += self.height_line
        self.pdf_canvas.drawString(0, y + self.delta_title, 'Pagador')
        sacado = boleto_dados.sacado

        # Linha grossa dividindo o Sacado
        y += self.height_line
        self.pdf_canvas.setLineWidth(2)
        self.__horizontalLine(0, y, self.width)
        self.pdf_canvas.setFont('Helvetica', self.font_size_value)
        for i in range(len(sacado)):
            self.pdf_canvas.drawString(
                15 * mm,
                (y - 10) - (i * self.delta_font),
                sacado[i]
            )
        self.pdf_canvas.setFont('Helvetica', self.font_size_title)

        # Linha vertical limitando todos os campos da direita
        self.pdf_canvas.setLineWidth(1)
        self.__verticalLine(self.width - (45 * mm), y, 9.5 * self.height_line)
        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.delta_title,
            '(=) Valor cobrado'
        )

        # Campos da direita
        y += self.height_line
        self.__horizontalLine(self.width - (45 * mm), y, 45 * mm)
        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.delta_title,
            '(+) Outros acréscimos'
        )

        y += self.height_line
        self.__horizontalLine(self.width - (45 * mm), y, 45 * mm)
        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.delta_title,
            '(+) Mora/Multa'
        )

        y += self.height_line
        self.__horizontalLine(self.width - (45 * mm), y, 45 * mm)
        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.delta_title,
            '(-) Outras deduções'
        )

        y += self.height_line
        self.__horizontalLine(self.width - (45 * mm), y, 45 * mm)
        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.delta_title,
            '(-) Descontos/Abatimentos'
        )
        self.pdf_canvas.drawString(
            0,
            y + self.delta_title,
            'Instruções'
        )

        self.pdf_canvas.setFont('Helvetica', self.font_size_value)
        instrucoes = boleto_dados.instrucoes
        for i in range(len(instrucoes)):
            self.pdf_canvas.drawString(
                2 * self.space,
                y - (i * self.delta_font),
                instrucoes[i]
            )
        self.pdf_canvas.setFont('Helvetica', self.font_size_title)

        # Linha horizontal com primeiro campo Uso do Banco
        y += self.height_line
        self.__horizontalLine(0, y, self.width)
        self.pdf_canvas.drawString(0, y + self.delta_title, 'Uso do banco')

        self.__verticalLine((30) * mm, y, 2 * self.height_line)
        self.pdf_canvas.drawString(
            (30 * mm) + self.space,
            y + self.delta_title,
            'Carteira'
        )

        self.__verticalLine((30 + 20) * mm, y, self.height_line)
        self.pdf_canvas.drawString(
            ((30 + 20) * mm) + self.space,
            y + self.delta_title,
            'Espécie'
        )

        self.__verticalLine(
            (30 + 20 + 20) * mm,
            y,
            2 * self.height_line
        )
        self.pdf_canvas.drawString(
            ((30 + 40) * mm) + self.space,
            y + self.delta_title,
            'Quantidade'
        )

        self.__verticalLine(
            (30 + 20 + 20 + 20 + 20) * mm, y, 2 * self.height_line)
        self.pdf_canvas.drawString(
            ((30 + 40 + 40) * mm) + self.space, y + self.delta_title, 'Valor')

        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.delta_title,
            '(=) Valor documento'
        )

        self.pdf_canvas.setFont('Helvetica', self.font_size_value)
        self.pdf_canvas.drawString(
            (30 * mm) + self.space,
            y + self.space,
            boleto_dados.carteira
        )
        self.pdf_canvas.drawString(
            ((30 + 20) * mm) + self.space,
            y + self.space,
            boleto_dados.especie
        )
        self.pdf_canvas.drawString(
            ((30 + 20 + 20) * mm) + self.space,
            y + self.space,
            boleto_dados.quantidade
        )
        valor = ''
        if boleto_dados.valor != '0.00':
            valor = self._formataValorParaExibir(boleto_dados.valor)
        self.pdf_canvas.drawString(
            ((30 + 20 + 20 + 20 + 20) * mm) + self.space,
            y + self.space,
            valor
        )
        valor_documento = self._formataValorParaExibir(
            boleto_dados.valor_documento
        )
        self.pdf_canvas.drawRightString(
            self.width - 2 * self.space,
            y + self.space,
            valor_documento
        )
        self.pdf_canvas.setFont('Helvetica', self.font_size_title)

        # Linha horizontal com primeiro campo Data documento
        y += self.height_line
        self.__horizontalLine(0, y, self.width)
        self.pdf_canvas.drawString(
            0,
            y + self.delta_title,
            'Data do documento'
        )
        self.pdf_canvas.drawString(
            (30 * mm) + self.space,
            y + self.delta_title,
            'N. do documento'
        )
        self.pdf_canvas.drawString(
            ((30 + 40) * mm) + self.space,
            y + self.delta_title,
            'Espécie doc'
        )
        self.__verticalLine(
            (30 + 20 + 20 + 20) * mm,
            y,
            self.height_line
        )
        self.pdf_canvas.drawString(
            ((30 + 40 + 20) * mm) + self.space,
            y + self.delta_title,
            'Aceite'
        )
        self.pdf_canvas.drawString(
            ((30 + 40 + 40) * mm) + self.space,
            y + self.delta_title,
            'Data processamento'
        )
        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.delta_title,
            'Nosso número'
        )

        self.pdf_canvas.setFont('Helvetica', self.font_size_value)
        self.pdf_canvas.drawString(
            0,
            y + self.space,
            boleto_dados.data_documento.strftime('%d/%m/%Y')
        )
        self.pdf_canvas.drawString(
            (30 * mm) + self.space,
            y + self.space,
            boleto_dados.numero_documento
        )
        self.pdf_canvas.drawString(
            ((30 + 40) * mm) + self.space,
            y + self.space,
            boleto_dados.especie_documento
        )
        self.pdf_canvas.drawString(
            ((30 + 40 + 20) * mm) + self.space,
            y + self.space,
            boleto_dados.aceite
        )
        self.pdf_canvas.drawString(
            ((30 + 40 + 40) * mm) + self.space,
            y + self.space,
            boleto_dados.data_processamento.strftime('%d/%m/%Y')
        )
        self.pdf_canvas.drawRightString(
            self.width - 2 * self.space,
            y + self.space,
            boleto_dados.format_nosso_numero()
        )
        self.pdf_canvas.setFont('Helvetica', self.font_size_title)

        # Linha horizontal com primeiro campo Cedente
        y += self.height_line
        self.__horizontalLine(0, y, self.width)
        self.pdf_canvas.drawString(0, y + self.delta_title + 10,
                                   'Beneficiário')
        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.delta_title + 10,
            boleto_dados.label_cedente
        )

        self.pdf_canvas.setFont('Helvetica', self.font_size_value)
        beneficiario = '{} - CPF/CNPJ: {}'.format(
            boleto_dados.cedente, boleto_dados.cedente_documento)
        self.pdf_canvas.drawString(0, y + self.space + 10, beneficiario)
        self.pdf_canvas.drawString(0, y + self.space,
                                   boleto_dados.cedente_endereco)
        self.pdf_canvas.drawRightString(
            self.width - 2 * self.space,
            y + self.space,
            boleto_dados.agencia_conta_cedente
        )
        self.pdf_canvas.setFont('Helvetica', self.font_size_title)

        # Linha horizontal com primeiro campo Local de Pagamento
        y += self.height_line + 10
        self.__horizontalLine(0, y, self.width)
        self.pdf_canvas.drawString(
            0,
            y + self.delta_title,
            'Local de pagamento'
        )
        self.pdf_canvas.drawString(
            self.width - (45 * mm) + self.space,
            y + self.delta_title,
            'Vencimento'
        )

        self.pdf_canvas.setFont('Helvetica', self.font_size_value)
        self.pdf_canvas.drawString(
            0,
            y + self.space,
            boleto_dados.local_pagamento
        )
        self.pdf_canvas.drawRightString(
            self.width - 2 * self.space,
            y + self.space,
            boleto_dados.data_vencimento.strftime('%d/%m/%Y')
        )
        self.pdf_canvas.setFont('Helvetica', self.font_size_title)

        # Linha grossa com primeiro campo logo tipo do banco
        self.pdf_canvas.setLineWidth(3)
        y += self.height_line
        self.__horizontalLine(0, y, self.width)
        self.pdf_canvas.setLineWidth(2)
        self.__verticalLine(40 * mm, y, self.height_line)  # Logo Tipo
        self.__verticalLine(60 * mm, y, self.height_line)  # Numero do Banco

        if boleto_dados.logo_image:
            logo_image_path = load_image(boleto_dados.logo_image)
            self.pdf_canvas.drawImage(
                logo_image_path,
                0,
                y + self.space + 1,
                40 * mm,
                self.height_line,
                preserveAspectRatio=True,
                anchor='sw'
            )
        self.pdf_canvas.setFont('Helvetica-Bold', 18)
        self.pdf_canvas.drawCentredString(
            50 * mm,
            y + 2 * self.space,
            boleto_dados.codigo_dv_banco
        )
        self.pdf_canvas.setFont('Helvetica-Bold', 11.5)
        self.pdf_canvas.drawRightString(
            self.width,
            y + 2 * self.space,
            boleto_dados.linha_digitavel
        )

        # Codigo de barras
        self._codigoBarraI25(boleto_dados.barcode, 2 * self.space, 0)

        self.pdf_canvas.restoreState()

        return self.width, (y + self.height_line)

    def drawBoletoCarneDuplo(self, boletoDados1, boletoDados2=None):
        """Imprime um boleto tipo carnê com 2 boletos por página.

        :param boletoDados1: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :param boletoDados2: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :type boletoDados1: :class:`pyboleto.data.BoletoData`
        :type boletoDados2: :class:`pyboleto.data.BoletoData`

        """
        y = 5 * mm
        d = self.drawBoletoCarne(boletoDados1, y)
        y += d[1] + 6 * mm
        # self._drawHorizontalCorteLine(0, y, d[0])
        y += 7 * mm
        if boletoDados2:
            self.drawBoletoCarne(boletoDados2, y)

    def drawBoletoCarne(self, boleto_dados, y):
        """Imprime apenas dos boletos do carnê.

        Esta função não deve ser chamada diretamente, ao invés disso use a
        drawBoletoCarneDuplo.

        :param boleto_dados: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :type boleto_dados: :class:`pyboleto.data.BoletoData`
        """
        x = 15 * mm
        d = self._draw_recibo_sacado_canhoto(boleto_dados, x, y)
        x += d[0] + 8 * mm
        self._drawVerticalCorteLine(x, y, d[1])
        x += 8 * mm
        d = self._drawReciboCaixa(boleto_dados, x, y)
        x += d[0]
        return x, d[1]

    def drawBoleto(self, boleto_dados):
        """Imprime Boleto Convencional

        Você pode chamar este método diversas vezes para criar um arquivo com
        várias páginas, uma por boleto.

        :param boleto_dados: Objeto com os dados do boleto a ser preenchido.
            Deve ser subclasse de :class:`pyboleto.data.BoletoData`
        :type boleto_dados: :class:`pyboleto.data.BoletoData`
        """
        x = 9 * mm  # margem esquerda
        y = 10 * mm  # margem inferior

        self._drawHorizontalCorteLine(x, y, self.width)
        y += 4 * mm  # distancia entre linha de corte e barcode

        d = self._drawReciboCaixa(boleto_dados, x, y)
        y += d[1] + (12 * mm)  # distancia entre Recibo caixa e linha de corte

        self._drawHorizontalCorteLine(x, y, self.width)

        y += 20 * mm
        d = self._drawReciboSacado(boleto_dados, x, y)
        y += d[1]
        return (self.width, y)

    def nextPage(self):
        """Força início de nova página"""

        self.pdf_canvas.showPage()

    def save(self):
        """Fecha boleto e constroi o arquivo"""

        self.pdf_canvas.save()

    def __horizontalLine(self, x, y, width):
        self.pdf_canvas.line(x, y, x + width, y)

    def __verticalLine(self, x, y, width):
        self.pdf_canvas.line(x, y, x, y + width)

    def _formataValorParaExibir(self, nfloat):
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        if nfloat:
            nfloat = float(nfloat)
            txt = locale.currency(nfloat, grouping=True, symbol=None)
        else:
            txt = ""
        return txt

    def _codigoBarraI25(self, num, x, y):
        """Imprime Código de barras otimizado para boletos

        O código de barras é otmizado para que o comprimento seja sempre o
        estipulado pela Febraban de 103mm.

        """
        # http://en.wikipedia.org/wiki/Interleaved_2_of_5

        altura = 13 * mm
        comprimento = 103 * mm

        thin_bar = 0.254320987654 * mm  # Tamanho correto aproximado

        bc = I2of5(num,
                   barWidth=thin_bar,
                   ratio=3,
                   barHeight=altura,
                   bearers=0,
                   quiet=0,
                   checksum=0)

        # Recalcula o tamanho do thin_bar para que o cod de barras tenha o
        # comprimento correto
        thin_bar = (thin_bar * comprimento) / bc.width
        bc.__init__(num, barWidth=thin_bar)

        bc.drawOn(self.pdf_canvas, x, y)


def load_image(logo_image):
    """Load Bank Image"""
    pyboleto_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(pyboleto_dir, 'media', logo_image)
    return image_path
