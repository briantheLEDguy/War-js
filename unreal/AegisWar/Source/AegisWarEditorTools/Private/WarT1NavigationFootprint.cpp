#include "WarT1NavigationAuthoringLibrary.h"

namespace
{
    double Cross(FVector2D A,FVector2D B) { return A.X*B.Y-A.Y*B.X; }
    double TwiceArea(const TArray<FVector2D>& P)
    {
        double Result=0;
        for (int32 I=0;I<P.Num();++I) Result+=Cross(P[I],P[(I+1)%P.Num()]);
        return Result;
    }
    bool OnSegment(FVector2D P,FVector2D A,FVector2D B)
    {
        return FMath::Abs(Cross(B-A,P-A))<1e-6
            && P.X>=FMath::Min(A.X,B.X)-1e-6 && P.X<=FMath::Max(A.X,B.X)+1e-6
            && P.Y>=FMath::Min(A.Y,B.Y)-1e-6 && P.Y<=FMath::Max(A.Y,B.Y)+1e-6;
    }
    bool Intersects(FVector2D A,FVector2D B,FVector2D C,FVector2D D)
    {
        const double AB1=Cross(B-A,C-A),AB2=Cross(B-A,D-A),CD1=Cross(D-C,A-C),CD2=Cross(D-C,B-C);
        return (AB1*AB2<0 && CD1*CD2<0) || OnSegment(A,C,D) || OnSegment(B,C,D)
            || OnSegment(C,A,B) || OnSegment(D,A,B);
    }
}

bool UWarT1NavigationAuthoringLibrary::IsPrivateCandidate(const FString& Package,FName Zone)
{
    if (Zone!=TEXT("sunmeadow_march") && Zone!=TEXT("cinderfen_outskirts")
        && Zone!=TEXT("brightfen_approach") && Zone!=TEXT("ashen_steppe")) return false;
    const FString Prefix=TEXT("/Game/WorldRebuild/T1Redesign_Atmosphere_");
    const FString Suffix=TEXT("_Navigation/")+Zone.ToString()+TEXT("/Review");
    if (!Package.StartsWith(Prefix) || !Package.EndsWith(Suffix)) return false;
    const FString Revision=Package.Mid(Prefix.Len(),Package.Len()-Prefix.Len()-Suffix.Len());
    if (Revision.Len()!=12) return false;
    for (const TCHAR C:Revision)
        if (!((C>=TEXT('0') && C<=TEXT('9')) || (C>=TEXT('a') && C<=TEXT('f')))) return false;
    return true;
}

bool UWarT1NavigationAuthoringLibrary::NavigationBounds(const FBox2D& Content,const TArray<FVector2D>& Outline,
    FBox2D& Result,FString& Error)
{
    Result=FBox2D(ForceInit);Error.Reset();
    if (!Content.bIsValid || Content.Min.ContainsNaN() || Content.Max.ContainsNaN()
        || Content.GetSize().GetMin()<=0 || Outline.Num()<3 || Outline.Num()>128)
    { Error=TEXT("Invalid navigation ownership or outline");return false; }
    for (const auto Point:Outline)
    {
        if (Point.ContainsNaN() || !Content.IsInsideOrOn(Point))
        { Result=FBox2D(ForceInit);Error=TEXT("Playable navigation outline escapes content ownership");return false; }
        Result+=Point;
    }
    TArray<TArray<FVector2D>> Cells;
    if (!ExteriorCells(Result,Outline,Cells,Error)) { Result=FBox2D(ForceInit);return false; }
    return true;
}

bool UWarT1NavigationAuthoringLibrary::ExteriorCells(const FBox2D& Bounds,const TArray<FVector2D>& Outline,
    TArray<TArray<FVector2D>>& Cells,FString& Error)
{
    Cells.Reset();Error.Reset();
    const auto Fail=[&](const TCHAR* Reason){Cells.Reset();Error=Reason;return false;};
    if (!Bounds.bIsValid || Bounds.Min.ContainsNaN() || Bounds.Max.ContainsNaN()
        || Bounds.GetSize().GetMin()<=0 || Bounds.GetSize().GetMax()>400000 || Outline.Num()<3 || Outline.Num()>128)
        return Fail(TEXT("Invalid or unbounded T1 navigation footprint"));
    for (int32 I=0;I<Outline.Num();++I)
    {
        const auto A=Outline[I],B=Outline[(I+1)%Outline.Num()];
        if (A.ContainsNaN() || !Bounds.IsInsideOrOn(A) || FVector2D::DistSquared(A,B)<1e-8)
            return Fail(TEXT("Footprint vertices must be finite, distinct and within content bounds"));
        for (int32 J=I+1;J<Outline.Num();++J)
        {
            if (J==I+1 || (I==0 && J==Outline.Num()-1)) continue;
            if (Intersects(A,B,Outline[J],Outline[(J+1)%Outline.Num()]))
                return Fail(TEXT("Navigation footprint must be simple, without crossing or touching nonadjacent edges"));
        }
    }
    const double InteriorArea=FMath::Abs(TwiceArea(Outline))*.5;
    if (InteriorArea<1) return Fail(TEXT("Navigation footprint is degenerate"));
    TArray<double> Cuts{Bounds.Min.Y,Bounds.Max.Y};
    for (const auto P:Outline) Cuts.AddUnique(P.Y);
    Cuts.Sort();
    // Between vertex heights every boundary is linear. Alternating ray crossings
    // partition each slab into inside intervals and exact convex exterior cells.
    for (int32 Row=1;Row<Cuts.Num();++Row)
    {
        const double Low=Cuts[Row-1],High=Cuts[Row],Middle=(Low+High)*.5;
        if (High-Low<1e-8) continue;
        struct FCrossing { double Middle,Low,High; };
        TArray<FCrossing> Crossings;
        for (int32 I=0;I<Outline.Num();++I)
        {
            const auto A=Outline[I],B=Outline[(I+1)%Outline.Num()];
            if ((A.Y>Middle)==(B.Y>Middle)) continue;
            const auto X=[&](double Y){return A.X+(B.X-A.X)*(Y-A.Y)/(B.Y-A.Y);};
            Crossings.Add({X(Middle),X(Low),X(High)});
        }
        Crossings.Sort([](const FCrossing& A,const FCrossing& B){return A.Middle<B.Middle;});
        if (Crossings.Num()%2) return Fail(TEXT("Footprint scanline cannot be paired"));
        double LeftLow=Bounds.Min.X,LeftHigh=Bounds.Min.X;
        for (int32 I=0;I<=Crossings.Num();I+=2)
        {
            const double RightLow=I<Crossings.Num() ? Crossings[I].Low : Bounds.Max.X;
            const double RightHigh=I<Crossings.Num() ? Crossings[I].High : Bounds.Max.X;
            TArray<FVector2D> Cell{{LeftLow,Low},{RightLow,Low},{RightHigh,High},{LeftHigh,High}};
            for (int32 J=Cell.Num()-1;J>=0;--J)
                if (Cell.Num()>2 && Cell[J].Equals(Cell[(J+1)%Cell.Num()],1e-6)) Cell.RemoveAt(J);
            if (TwiceArea(Cell)>1e-4) Cells.Add(MoveTemp(Cell));
            if (I<Crossings.Num()) {LeftLow=Crossings[I+1].Low;LeftHigh=Crossings[I+1].High;}
        }
    }
    double ExteriorArea=0;
    for (const auto& Cell:Cells) ExteriorArea+=TwiceArea(Cell)*.5;
    const double RectangleArea=Bounds.GetSize().X*Bounds.GetSize().Y;
    if (Cells.Num()>1024 || FMath::Abs(ExteriorArea+InteriorArea-RectangleArea)>FMath::Max(1.,RectangleArea*1e-10))
        return Fail(TEXT("Footprint complement coverage differs from its bounded content rectangle"));
    return true;
}
