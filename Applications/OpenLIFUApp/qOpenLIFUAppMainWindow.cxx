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

// OpenLIFU includes
#include "qOpenLIFUAppMainWindow.h"
#include "qOpenLIFUAppMainWindow_p.h"

// Qt includes
#include <QDesktopWidget>
#include <QLabel>
#include <QMessageBox>

// Slicer includes
#include "qSlicerApplication.h"
#include "qSlicerMainWindow_p.h"
#include "qSlicerModuleSelectorToolBar.h"
#include "qMRMLWidget.h"
#include "vtkSlicerVersionConfigure.h"

//-----------------------------------------------------------------------------
// qOpenLIFUAppMainWindowPrivate methods

qOpenLIFUAppMainWindowPrivate::qOpenLIFUAppMainWindowPrivate(qOpenLIFUAppMainWindow& object)
  : Superclass(object)
{
}

//-----------------------------------------------------------------------------
qOpenLIFUAppMainWindowPrivate::~qOpenLIFUAppMainWindowPrivate()
{
}

//-----------------------------------------------------------------------------
void qOpenLIFUAppMainWindowPrivate::init()
{
#if (QT_VERSION >= QT_VERSION_CHECK(5, 7, 0))
  QApplication::setAttribute(Qt::AA_UseHighDpiPixmaps);
#endif
  Q_Q(qOpenLIFUAppMainWindow);
  this->Superclass::init();
}

//-----------------------------------------------------------------------------
void qOpenLIFUAppMainWindowPrivate::setupUi(QMainWindow * mainWindow)
{
  qSlicerApplication * app = qSlicerApplication::application();

  //----------------------------------------------------------------------------
  // Add actions
  //----------------------------------------------------------------------------
  QAction* helpAboutOpenLIFUAppAction = new QAction(mainWindow);
  helpAboutOpenLIFUAppAction->setObjectName("HelpAboutOpenLIFUAppAction");
  helpAboutOpenLIFUAppAction->setText("About " + app->mainApplicationName());

  //----------------------------------------------------------------------------
  // Calling "setupUi()" after adding the actions above allows the call
  // to "QMetaObject::connectSlotsByName()" done in "setupUi()" to
  // successfully connect each slot with its corresponding action.
  this->Superclass::setupUi(mainWindow);

  // Add Help Menu Action
  this->HelpMenu->addAction(helpAboutOpenLIFUAppAction);

  //----------------------------------------------------------------------------
  // Configure
  //----------------------------------------------------------------------------
  mainWindow->setWindowIcon(QIcon(":/Icons/Medium/DesktopIcon.png"));

  QLabel* logoLabel = new QLabel();
  logoLabel->setObjectName("LogoLabel");
  logoLabel->setPixmap(qMRMLWidget::pixmapFromIcon(QIcon(":/LogoFull.png")));
  this->PanelDockWidget->setTitleBarWidget(logoLabel);

  // Hide the menus
  //this->menubar->setVisible(false);
  //this->FileMenu->setVisible(false);
  //this->EditMenu->setVisible(false);
  //this->ViewMenu->setVisible(false);
  //this->LayoutMenu->setVisible(false);
  //this->HelpMenu->setVisible(false);
}

//-----------------------------------------------------------------------------
// qOpenLIFUAppMainWindow methods

//-----------------------------------------------------------------------------
qOpenLIFUAppMainWindow::qOpenLIFUAppMainWindow(QWidget* windowParent)
  : Superclass(new qOpenLIFUAppMainWindowPrivate(*this), windowParent)
{
  Q_D(qOpenLIFUAppMainWindow);
  d->init();
}

//-----------------------------------------------------------------------------
qOpenLIFUAppMainWindow::qOpenLIFUAppMainWindow(
  qOpenLIFUAppMainWindowPrivate* pimpl, QWidget* windowParent)
  : Superclass(pimpl, windowParent)
{
  // init() is called by derived class.
}

//-----------------------------------------------------------------------------
qOpenLIFUAppMainWindow::~qOpenLIFUAppMainWindow()
{
}

//-----------------------------------------------------------------------------
void qOpenLIFUAppMainWindow::on_HelpAboutOpenLIFUAppAction_triggered()
{
  qSlicerApplication* app = qSlicerApplication::application();
  const QString applicationName = app->mainApplicationName();
  const QString text = QString(
    "<h3>%1</h3>"
    "<p>An open-source software platform for Low Intensity Focused Ultrasound (LIFU).</p>"
    "<p>OpenLIFU version: %2 (%3)</p>"
    "<p>Version details: 3D Slicer %4 (r%5 / %6)</p>"
    "<p><strong>CAUTION - Investigational device.</strong> Limited by Federal "
    "(or United States) law to investigational use. The system described here "
    "has <em>not</em> been evaluated by the FDA and is not designed for the "
    "treatment or diagnosis of any disease. It is provided AS-IS, with no "
    "warranties. User assumes all liability and responsibility for identifying "
    "and mitigating risks associated with using this software.</p>")
    .arg(applicationName.toHtmlEscaped())
    .arg(app->applicationVersion().toHtmlEscaped())
    .arg(app->mainApplicationRepositoryRevision().toHtmlEscaped())
    .arg(QString(Slicer_VERSION_FULL).toHtmlEscaped())
    .arg(app->revision().toHtmlEscaped())
    .arg(app->repositoryRevision().toHtmlEscaped());

  QMessageBox::about(this, tr("About %1").arg(applicationName), text);
}
