/*==============================================================================

  Copyright (c) Kitware, Inc.

  See http://www.slicer.org/copyright/copyright.txt for details.

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.

  This file was originally developed by Julien Finet, Kitware, Inc.
  and was partially funded by NIH grant 3P41RR013218-12S1

==============================================================================*/

// Qt includes
#include <QDebug>
#include <QLinearGradient>
#include <QMenuBar>
#include <QPainter>
#include <QPalette>
#include <QPushButton>
#include <QStyleFactory>
#include <QStyleOption>
#include <QToolBar>

// CTK includes
#include <ctkCollapsibleButton.h>
#include <ctkSettingsDialog.h>

// Slicer includes
#include "qSlicerApplication.h"
#include "qSlicerSettingsStylesPanel.h"

// OpenLIFU includes
#include "qAppStyle.h"

// --------------------------------------------------------------------------
// qAppStyle methods

// --------------------------------------------------------------------------
qAppStyle::qAppStyle()
{
  // Slicer uses a QCleanlooksStyle as base style.
  this->setBaseStyle(new QProxyStyle(QStyleFactory::create("fusion")));
}

// --------------------------------------------------------------------------
qAppStyle::~qAppStyle()
{
}

//------------------------------------------------------------------------------
void qAppStyle::configureApplication(qSlicerApplication& app)
{
  auto* stylesPanel = app.settingsDialog()->findChild<qSlicerSettingsStylesPanel*>();
  auto applyAppStyle = [&app, stylesPanel]()
    {
    if (stylesPanel && stylesPanel->currentStyle() != "Dark Slicer")
      {
      stylesPanel->setCurrentStyle("Dark Slicer");
      return;
      }
    app.removeEventFilter(app.style());
    app.setStyle(new qAppStyle);
    app.setPalette(app.style()->standardPalette());
    app.installEventFilter(app.style());
    };

  // Keep the custom style when appearance settings are loaded or reset.
  if (stylesPanel)
    {
    QObject::connect(stylesPanel, &qSlicerSettingsStylesPanel::currentStyleChanged,
                     &app, applyAppStyle);
    }
  applyAppStyle();
  if (stylesPanel)
    {
    stylesPanel->applySettings();
    }
}

//------------------------------------------------------------------------------
QPalette qAppStyle::standardPalette()const
{
  QPalette palette = this->Superclass::standardDarkPalette();

  palette.setColor(QPalette::Active, QPalette::Window, "#1E1E20");
  palette.setColor(QPalette::Inactive, QPalette::Window, "#1E1E20");
  palette.setColor(QPalette::Disabled, QPalette::Window, "#29292B");
  palette.setColor(QPalette::Active, QPalette::WindowText, "#FFFFFF");
  palette.setColor(QPalette::Inactive, QPalette::WindowText, "#BDC3C7");
  palette.setColor(QPalette::Disabled, QPalette::WindowText, "#6B7480");
  palette.setColor(QPalette::Active, QPalette::Text, "#FFFFFF");
  palette.setColor(QPalette::Inactive, QPalette::Text, "#BDC3C7");
  palette.setColor(QPalette::Disabled, QPalette::Text, "#6B7480");
  palette.setColor(QPalette::Active, QPalette::Base, "#222222");
  palette.setColor(QPalette::Inactive, QPalette::Base, "#222222");
  palette.setColor(QPalette::Disabled, QPalette::Base, "#1B1D22");


  palette.setColor(QPalette::Light, "#3E4E6F");
  palette.setColor(QPalette::Button, "#3A3F4B");
  palette.setColor(QPalette::Mid, "#3E4E6F");
  palette.setColor(QPalette::Dark, "#3E4E6F");
  palette.setColor(QPalette::Active, QPalette::ButtonText, "#FFFFFF");
  palette.setColor(QPalette::Inactive, QPalette::ButtonText, "#FFFFFF");
  palette.setColor(QPalette::Disabled, QPalette::ButtonText, "#888888");
  palette.setColor(QPalette::Shadow, "#0F0F10");

  palette.setColor(QPalette::Highlight, "#269cf6");
  palette.setColor(QPalette::HighlightedText, "#ffffff");

  palette.setColor(QPalette::Active, QPalette::AlternateBase, "#252525");
  palette.setColor(QPalette::Inactive, QPalette::AlternateBase, "#252525");
  palette.setColor(QPalette::ToolTipBase, "#1E1E20");
  palette.setColor(QPalette::ToolTipText, "#FFFFFF");

  return palette;
}

//------------------------------------------------------------------------------
void qAppStyle::drawComplexControl(ComplexControl control,
                                   const QStyleOptionComplex* option,
                                   QPainter* painter,
                                   const QWidget* widget )const
{
  const_cast<QStyleOptionComplex*>(option)->palette =
    this->tweakWidgetPalette(option->palette, widget);
  this->Superclass::drawComplexControl(control, option, painter, widget);
}

//------------------------------------------------------------------------------
void qAppStyle::drawControl(ControlElement element,
                            const QStyleOption* option,
                            QPainter* painter,
                            const QWidget* widget )const
{
  const_cast<QStyleOption*>(option)->palette =
    this->tweakWidgetPalette(option->palette, widget);

  // For some reason the toolbar paint routine is not respecting the palette.
  // here we make sure the background is correctly drawn.
  if (element == QStyle::CE_ToolBar &&
      qobject_cast<const QToolBar*>(widget))
    {
    painter->fillRect(option->rect, option->palette.brush(QPalette::Window));
    }
  this->Superclass::drawControl(element, option, painter, widget);
}

//------------------------------------------------------------------------------
void qAppStyle::drawPrimitive(PrimitiveElement element,
                              const QStyleOption* option,
                              QPainter* painter,
                              const QWidget* widget )const
{
  const_cast<QStyleOption*>(option)->palette =
    this->tweakWidgetPalette(option->palette, widget);
  this->Superclass::drawPrimitive(element, option, painter, widget);
}

//------------------------------------------------------------------------------
QPalette qAppStyle::tweakWidgetPalette(QPalette widgetPalette,
                                       const QWidget* widget)const
{
  if (!widget)
    {
    return widgetPalette;
    }
  const QPushButton* pushButton =
    qobject_cast<const QPushButton*>(widget);
  if (pushButton &&
      !pushButton->text().isEmpty())
    {
    QColor buttonColor = this->standardPalette().color(QPalette::Dark);
    widgetPalette.setColor(QPalette::Active, QPalette::Button, buttonColor);
    widgetPalette.setColor(QPalette::Inactive, QPalette::Button, buttonColor);
    QColor disabledButtonColor = buttonColor.toHsv();
    disabledButtonColor.setHsvF(disabledButtonColor.hueF(),
                                disabledButtonColor.saturationF() * 0.8,
                                disabledButtonColor.valueF() * 0.9);
    widgetPalette.setColor(QPalette::Disabled, QPalette::Button, disabledButtonColor);
    QColor buttonTextColor =
      this->standardPalette().color(QPalette::Light);
    widgetPalette.setColor(QPalette::Active, QPalette::ButtonText, buttonTextColor);
    widgetPalette.setColor(QPalette::Inactive, QPalette::ButtonText, buttonTextColor);
    QColor disabledButtonTextColor = buttonTextColor.toHsv();
    disabledButtonTextColor.setHsvF(buttonColor.hueF(),
                                    disabledButtonTextColor.saturationF() * 0.3,
                                    disabledButtonTextColor.valueF() * 0.8);
    widgetPalette.setColor(QPalette::Disabled, QPalette::ButtonText, disabledButtonColor);
    }
  if (qobject_cast<const QMenuBar*>(widget))
    {
    QColor highlightColor = this->standardPalette().color(QPalette::Dark);
    //QBrush highlightBrush = this->standardPalette().brush(QPalette::Dark);
    QColor highlightTextColor =
      this->standardPalette().color(QPalette::Light);
    QBrush highlightTextBrush =
      this->standardPalette().brush(QPalette::Light);
    QColor darkColor = this->standardPalette().color(QPalette::Highlight);
    QColor lightColor =
      this->standardPalette().color(QPalette::HighlightedText);

    QLinearGradient hilightGradient(0., 0., 0., 1.);
    hilightGradient.setCoordinateMode(QGradient::ObjectBoundingMode);
    hilightGradient.setColorAt(0., highlightColor);
    hilightGradient.setColorAt(1., highlightColor.darker(120));
    QBrush highlightBrush(hilightGradient);

    widgetPalette.setColor(QPalette::Highlight, darkColor);
    widgetPalette.setColor(QPalette::HighlightedText, lightColor);

    widgetPalette.setColor(QPalette::Window, highlightColor);
    widgetPalette.setColor(QPalette::WindowText, highlightTextColor);
    widgetPalette.setColor(QPalette::Base, highlightColor);
    widgetPalette.setColor(QPalette::Text, highlightTextColor);
    widgetPalette.setColor(QPalette::Button, highlightColor);
    widgetPalette.setColor(QPalette::ButtonText, highlightTextColor);

    widgetPalette.setBrush(QPalette::Window, highlightBrush);
    widgetPalette.setBrush(QPalette::WindowText, highlightTextBrush);
    widgetPalette.setBrush(QPalette::Base, highlightBrush);
    widgetPalette.setBrush(QPalette::Text, highlightTextBrush);
    widgetPalette.setBrush(QPalette::Button, highlightBrush);
    widgetPalette.setBrush(QPalette::ButtonText, highlightTextBrush);
    }
/*
  QWidget* parentWidget = widget->parentWidget();
  QWidget* grandParentWidget = parentWidget? parentWidget->parentWidget() : 0;
  if (qobject_cast<const QToolBar*>(widget) ||
      qobject_cast<QToolBar*>(parentWidget) ||
      qobject_cast<QToolBar*>(grandParentWidget))
    {
    QColor windowColor = this->standardPalette().color(QPalette::Window);

    //QColor highlightColor = this->standardPalette().color(QPalette::Highlight);
    //QColor highlightTextColor =
    //  this->standardPalette().color(QPalette::HighlightedText);
    //QColor darkColor = this->standardPalette().color(QPalette::Dark);
    //QColor lightColor =
    //  this->standardPalette().color(QPalette::Light);
    QColor highlightColor = this->standardPalette().color(QPalette::Dark);
    //QBrush highlightBrush = this->standardPalette().brush(QPalette::Dark);
    QBrush highlightTextBrush =
      this->standardPalette().brush(QPalette::Light);
    QColor darkColor = this->standardPalette().color(QPalette::Highlight);
    QColor lightColor =
      this->standardPalette().color(QPalette::HighlightedText);

    QLinearGradient hilightGradient(0., 0., 0., 1.);
    hilightGradient.setCoordinateMode(QGradient::ObjectBoundingMode);

    hilightGradient.setColorAt(0., highlightColor);
    hilightGradient.setColorAt(1., highlightColor.darker(140));
    QBrush highlightBrush(hilightGradient);

    widgetPalette.setColor(QPalette::Highlight, darkColor);
    widgetPalette.setColor(QPalette::HighlightedText, lightColor);
    widgetPalette.setBrush(QPalette::Window, highlightBrush);
    widgetPalette.setBrush(QPalette::WindowText, highlightTextBrush);
    widgetPalette.setBrush(QPalette::Base, highlightBrush);
    widgetPalette.setBrush(QPalette::Text, highlightTextBrush);
    widgetPalette.setBrush(QPalette::Button, highlightBrush);
    widgetPalette.setBrush(QPalette::ButtonText, highlightTextBrush);
    }
*/
  return widgetPalette;
}

//------------------------------------------------------------------------------
void qAppStyle::polish(QWidget* widget)
{
  this->Superclass::polish(widget);
  ctkCollapsibleButton* collapsibleButton =
    qobject_cast<ctkCollapsibleButton*>(widget);
  if (collapsibleButton)
    {
    collapsibleButton->setFlat(true);
    collapsibleButton->setContentsFrameShadow(QFrame::Sunken);
    }
}
