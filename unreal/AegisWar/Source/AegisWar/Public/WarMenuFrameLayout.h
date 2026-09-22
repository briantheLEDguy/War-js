#pragma once
#include "CoreMinimal.h"

namespace WarMenuFrame
{
    inline constexpr double Width=1672, Height=941;
    // Five columns preserve the centre crest as well as both corner ornaments.
    inline constexpr double SourceX[]={0,220,650,1022,1452,Width};
    inline constexpr double SourceY[]={0,460,650,Height};
    struct FLayout { double X[6],Y[4]; };
    inline FLayout Layout(FVector2D Size,double OrnamentScale)
    {
        const double Scale=FMath::Max(0.,FMath::Min3(OrnamentScale,Size.X/Width,Size.Y/Height));
        const double Corner=220*Scale, Crest=372*Scale;
        return {{0,Corner,(Size.X-Crest)/2,(Size.X+Crest)/2,Size.X-Corner,Size.X},
            {0,460*Scale,Size.Y-291*Scale,Size.Y}};
    }
}
