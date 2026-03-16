using System.Windows;
using GaoGaoWorkSpace.Core.Models;
using GaoGaoWorkSpace.UI.ViewModels;

namespace GaoGaoWorkSpace.App;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
        Loaded += OnLoaded;
    }

    private async void OnLoaded(object sender, RoutedEventArgs e)
    {
        if (DataContext is MainViewModel vm)
        {
            await vm.InitializeAsync();
        }
    }

    private void TreeView_SelectedItemChanged(object sender, RoutedPropertyChangedEventArgs<object> e)
    {
        if (DataContext is not MainViewModel vm) return;
        if (e.NewValue is TreeNodeModel node)
        {
            vm.SelectedNode = node;
        }
    }
}
