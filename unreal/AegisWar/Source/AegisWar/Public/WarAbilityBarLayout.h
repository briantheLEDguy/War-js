#pragma once
#include "CoreMinimal.h"

namespace WarAbilityBarLayout
{
    constexpr double InnerSize = 84.;
    constexpr double Pitch = InnerSize * 870. / 764.;
    struct FArtwork
    {
        const TCHAR* File;
        FVector2D SourceSize;
        FBox2D Inner;
        FBox2D Visible;
    };
    inline FArtwork Artwork(int32 Index, int32 Count)
    {
        FArtwork Art{TEXT("abilitybarsingle.png"),{1254,1254},{{244,283},{1008,963}},{{106,120},{1148,1128}}};
        if (Count > 1 && Index == 0)
            Art = {TEXT("leftendcap-abilitybar.png"),{1374,1145},{{600,382},{1058,780}},{{202,128},{1180,1012}}};
        else if (Count > 1 && Index == Count-1)
            Art = {TEXT("rightendcap-abilitybar.png"),{1374,1145},{{180,320},{764,835}},{{54,22},{1330,1112}}};
        // Crop shared rails at the cell boundary. Adjacent gold edges meet without transparent gutters.
        const double HalfRail = (Pitch/InnerSize-1.) * Art.Inner.GetSize().X / 2.;
        if (Index > 0) Art.Visible.Min.X = Art.Inner.Min.X-HalfRail;
        if (Index < Count-1) Art.Visible.Max.X = Art.Inner.Max.X+HalfRail;
        return Art;
    }
    inline FMargin Padding(int32 Count) { return Count > 1 ? FMargin(70,54,80,50) : FMargin(10,22,10,22); }
    inline FVector2D Size(int32 Count)
    {
        const FMargin P = Padding(Count);
        return {Count*Pitch+P.Left+P.Right,26+P.Top+InnerSize+P.Bottom};
    }
    inline FVector2D Fit(FVector2D View, int32 Count)
    {
        const FVector2D Desired = Size(Count);
        const double Scale = FMath::Clamp(FMath::Min((View.X-12)/Desired.X,(View.Y-12)/Desired.Y),.01,1.);
        return Desired*Scale;
    }
}
