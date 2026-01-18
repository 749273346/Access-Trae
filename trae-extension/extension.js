const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

function activate(context) {
    // Determine the materials directory (assuming it's in the workspace root or parent)
    // For MVP, we hardcode relative to the workspace folder if opened
    const workspaceFolders = vscode.workspace.workspaceFolders;
    let materialsPath = '';
    
    if (workspaceFolders) {
        materialsPath = path.join(workspaceFolders[0].uri.fsPath, 'materials');
    }

    // Provider for the TreeView
    const clipProvider = new ClipProvider(materialsPath);
    vscode.window.registerTreeDataProvider('traeDoubaoClips', clipProvider);

    // Refresh Command
    vscode.commands.registerCommand('traeDoubao.refresh', () => clipProvider.refresh());

    // Insert Command
    vscode.commands.registerCommand('traeDoubao.insertClip', (item) => {
        if (!item) return;
        const filePath = path.join(materialsPath, item.label);
        
        fs.readFile(filePath, 'utf8', (err, data) => {
            if (err) {
                vscode.window.showErrorMessage(`Error reading file: ${err.message}`);
                return;
            }
            
            const editor = vscode.window.activeTextEditor;
            if (editor) {
                editor.edit(editBuilder => {
                    editBuilder.insert(editor.selection.active, data);
                });
            } else {
                // If no editor open, open the document
                vscode.workspace.openTextDocument(filePath).then(doc => {
                    vscode.window.showTextDocument(doc);
                });
            }
        });
    });
}

class ClipProvider {
    constructor(rootPath) {
        this.rootPath = rootPath;
        this._onDidChangeTreeData = new vscode.EventEmitter();
        this.onDidChangeTreeData = this._onDidChangeTreeData.event;
    }

    refresh() {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element) {
        return element;
    }

    getChildren(element) {
        if (!this.rootPath) {
            vscode.window.showInformationMessage('No workspace open');
            return Promise.resolve([]);
        }

        if (!fs.existsSync(this.rootPath)) {
            return Promise.resolve([]);
        }

        if (element) {
            return Promise.resolve([]);
        } else {
            return new Promise((resolve) => {
                fs.readdir(this.rootPath, (err, files) => {
                    if (err) {
                        resolve([]);
                    } else {
                        const items = files
                            .filter(file => file.endsWith('.md'))
                            .sort((a, b) => {
                                // Sort by time (newest first)
                                return fs.statSync(path.join(this.rootPath, b)).mtime.getTime() - 
                                       fs.statSync(path.join(this.rootPath, a)).mtime.getTime();
                            })
                            .map(file => {
                                const item = new vscode.TreeItem(file, vscode.TreeItemCollapsibleState.None);
                                item.command = {
                                    command: 'traeDoubao.insertClip',
                                    title: 'Insert',
                                    arguments: [item]
                                };
                                return item;
                            });
                        resolve(items);
                    }
                });
            });
        }
    }
}

function deactivate() {}

module.exports = {
    activate,
    deactivate
};
