#pragma once
#include "Widgets/SCompoundWidget.h"
#include "Brushes/SlateDynamicImageBrush.h"
#include "WarMenuFrameLayout.h"
#include "Misc/Paths.h"
#include "Rendering/DrawElements.h"

/** Resizes the owner's original artwork without distorting its crest/corners. */
class SWarMenuFrame : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SWarMenuFrame) : _ArtScale(.2f) {}
        SLATE_ARGUMENT(float,ArtScale)
        SLATE_DEFAULT_SLOT(FArguments,Content)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args)
    {
        ArtScale=Args._ArtScale;
        Texture=MakeShared<FSlateDynamicImageBrush>(FName(*FPaths::Combine(FPaths::ProjectContentDir(),TEXT("UI/menuback.png"))),
            FVector2D(WarMenuFrame::Width,WarMenuFrame::Height));
        for (int32 Y=0;Y<3;++Y) for (int32 X=0;X<5;++X)
        {
            FSlateBrush Brush=*Texture;
            Brush.SetUVRegion(FBox2D(FVector2D(WarMenuFrame::SourceX[X]/WarMenuFrame::Width,WarMenuFrame::SourceY[Y]/WarMenuFrame::Height),
                FVector2D(WarMenuFrame::SourceX[X+1]/WarMenuFrame::Width,WarMenuFrame::SourceY[Y+1]/WarMenuFrame::Height)));
            Slices.Add(Brush);
        }
        ChildSlot.Padding(FMargin(124*ArtScale+12,460*ArtScale+8,124*ArtScale+12,291*ArtScale+10))[Args._Content.Widget];
    }
    virtual int32 OnPaint(const FPaintArgs& Args,const FGeometry& Geometry,const FSlateRect& Cull,
        FSlateWindowElementList& Elements,int32 Layer,const FWidgetStyle& Style,bool Enabled) const override
    {
        const auto Layout=WarMenuFrame::Layout(Geometry.GetLocalSize(),ArtScale);
        for (int32 Y=0;Y<3;++Y) for (int32 X=0;X<5;++X)
            FSlateDrawElement::MakeBox(Elements,Layer,Geometry.ToPaintGeometry(
                FVector2D(Layout.X[X+1]-Layout.X[X],Layout.Y[Y+1]-Layout.Y[Y]),
                FSlateLayoutTransform(FVector2D(Layout.X[X],Layout.Y[Y]))),&Slices[Y*5+X],ESlateDrawEffect::None,
                Style.GetColorAndOpacityTint());
        // Repeat the stone at a uniform aspect ratio; alternate direction so tile edges match.
        const double Scale=Layout.Y[1]/460;
        const double Left=128*Scale, StoneWidth=Geometry.GetLocalSize().X-256*Scale;
        const double TileHeight=FMath::Max(1.,StoneWidth*190/1416);
        int32 Tile=0;
        for (double Top=Layout.Y[1];Top<Layout.Y[2];Top+=TileHeight,++Tile)
        {
            const double Height=FMath::Min(TileHeight,Layout.Y[2]-Top),Fraction=Height/TileHeight;
            const double Start=Tile%2 ? 650 : 460,End=Start+(Tile%2 ? -190 : 190)*Fraction;
            FSlateBrush Stone=*Texture;
            Stone.SetUVRegion(FBox2D(FVector2D(128/1672.,Start/941.),FVector2D(1544/1672.,End/941.)));
            FSlateDrawElement::MakeBox(Elements,Layer+1,Geometry.ToPaintGeometry(FVector2D(StoneWidth,Height),
                FSlateLayoutTransform(FVector2D(Left,Top))),&Stone,ESlateDrawEffect::None,Style.GetColorAndOpacityTint());
        }
        return SCompoundWidget::OnPaint(Args,Geometry,Cull,Elements,Layer+2,Style,Enabled);
    }
private:
    float ArtScale=.2f;
    TSharedPtr<FSlateDynamicImageBrush> Texture;
    TArray<FSlateBrush> Slices;
};
