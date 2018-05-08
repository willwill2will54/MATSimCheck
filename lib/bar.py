import progressbar


def BAR():
    return progressbar.ProgressBar(widgets=[
        progressbar.AnimatedMarker(markers='⣯⣟⡿⢿⣻⣽⣾⣷'),
        ' [', progressbar.Percentage(), '] ',
        progressbar.Bar(marker='■', fill='□', left='[', right=']'),
        ' (', progressbar.ETA(), ') ', ], redirect_stdout=True)
